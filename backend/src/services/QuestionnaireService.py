"""Service for managing questionnaires and user responses."""
import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from collections import deque
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
import time
from ..utils.cache.redis_client import (
    get_cache, set_cache, delete_cache, get_questionnaire_cache_key
)
from ..config.constant import CONTINUATION_PROMPT_ID
from ..models.mongo_db import get_mongo_db

logger = logging.getLogger(__name__)

class QuestionnaireService:
    """Service for managing questionnaires and user responses."""
    
    def __init__(self, db_session: AsyncSession = None):
        """
        Initialize the questionnaire service.
        
        Args:
            db_session: SQLAlchemy async session for database access (can be None)
        """
        self.db_session = db_session # Kept for potential future use, but not for state
        self.mongo_db = get_mongo_db()
        self.basic_information_questions = {}
        self.dynamic_questionnaire = {}
        self.question_graph = {}
        self.current_version = 1
        self.total_questions = 0
        self.initial_participating_questions_count = 0
        self.added_participating_questions_count = 0
        
    async def load_questions(self):
        """
        Asynchronously loads questions from MongoDB.
        This must be called before using the service.
        """
        if self.basic_information_questions and self.dynamic_questionnaire:
            logger.debug("Questions already loaded.")
            return

        await self._load_questions_from_db()
        self.question_graph = self._build_question_graph()
        logger.info(f"Built question graph with {len(self.question_graph)} entries")

    async def _load_questions_from_db(self):
        """
        Loads questionnaire data from MongoDB collections.
        """
        if self.mongo_db is None:
            logger.error("MongoDB client not available. Cannot load questions.")
            self._create_default_questions()
            return

        try:
            logger.info("Loading basic information questions from MongoDB...")
            basic_questions_cursor = self.mongo_db.basic_questions.find({}, {'_id': 0})
            basic_questions_list = await basic_questions_cursor.to_list(length=None)
            
            if not basic_questions_list:
                logger.error("'basic_questions' collection is empty or does not exist.")
            
            self.basic_information_questions = {q['id']: q for q in basic_questions_list}
            logger.info(f"Loaded {len(self.basic_information_questions)} basic information questions from MongoDB.")

            logger.info("Loading dynamic questionnaire questions from MongoDB...")
            dynamic_questions_cursor = self.mongo_db.dynamic_questions.find({}, {'_id': 0})
            dynamic_questions_list = await dynamic_questions_cursor.to_list(length=None)

            if not dynamic_questions_list:
                logger.error("'dynamic_questions' collection is empty or does not exist.")
            
            self.dynamic_questionnaire = {q['id']: q for q in dynamic_questions_list}
            logger.info(f"Loaded {len(self.dynamic_questionnaire)} dynamic questions from MongoDB.")

        except Exception as e:
            logger.error(f"Error loading questionnaire data from MongoDB: {e}", exc_info=True)
            self._create_default_questions()

    def _build_question_graph(self) -> Dict[str, Dict[str, Any]]:
        """
        Builds a complete, recursive graph of all questions and their dependencies.
        """
        graph = {}
        self.total_questions = 0

        all_question_data = {**self.basic_information_questions, **self.dynamic_questionnaire}
        
        for q_id, question_data in all_question_data.items():
            self._build_node_recursively(graph, question_data)
        
        basic_question_list = list(self.basic_information_questions.values())
        for i, question in enumerate(basic_question_list):
            if i + 1 < len(basic_question_list):
                next_q_id = basic_question_list[i + 1]['id']
                if question['id'] in graph:
                    graph[question['id']]['next_default'] = next_q_id
        
        return graph

    def _build_node_recursively(self, graph: Dict, question_data: Dict):
        """
        Recursively builds a node for a question and any questions nested inside it.
        """
        q_id = question_data.get('id')
        if not q_id or q_id in graph:
            return

        graph[q_id] = self._create_graph_node(None)
        self.total_questions += 1
        
        if 'branches' in question_data:
            graph[q_id]['branches'] = question_data['branches']
            
        if 'on_answered' in question_data:
            conditional_q = question_data['on_answered']
            graph[q_id]['on_answered'] = conditional_q
            self._build_node_recursively(graph, conditional_q)

        if 'on_unanswered' in question_data:
            conditional_q = question_data['on_unanswered']
            graph[q_id]['on_unanswered'] = conditional_q
            self._build_node_recursively(graph, conditional_q)

    def _create_graph_node(self, next_default) -> Dict[str, Any]:
        """Helper to create a standard graph node structure."""
        return {"next_default": next_default, "branches": {}, "on_answered": {}, "on_unanswered": {}}

    async def _get_user_state_from_db(self, user_id: str) -> Optional[Dict[str, Any]]:
        if self.mongo_db is None: return None
        try:
            state_record = await self.mongo_db.questionnaire_states.find_one({"user_id": user_id})
            if not state_record: return None
            state_record['queue'] = deque(state_record.get('queue', []))
            return state_record
        except Exception as e:
            logger.error(f"Error retrieving user state from MongoDB: {e}")
            return None
            
    async def _update_user_state_in_db(self, user_id: str, state: Dict[str, Any]) -> bool:
        if self.mongo_db is None: return False
        try:
            mongo_state = state.copy()
            mongo_state['queue'] = list(mongo_state.get('queue', []))
            mongo_state['last_updated'] = datetime.now(timezone.utc)

            if 'user_id' in mongo_state: del mongo_state['user_id']
            if 'created_at' in mongo_state: del mongo_state['created_at']
            if 'start_time' in mongo_state: del mongo_state['start_time']
            if '_id' in mongo_state: del mongo_state['_id']

            await self.mongo_db.questionnaire_states.update_one(
                {"user_id": user_id},
                {"$set": mongo_state, "$setOnInsert": {"user_id": user_id, "created_at": datetime.now(timezone.utc)}},
                upsert=True
            )
            return True
        except Exception as e:
            logger.error(f"Error updating user state in MongoDB: {e}", exc_info=True)
            return False
            
    async def _delete_user_state_from_db(self, user_id: str) -> bool:
        if self.mongo_db is None: return False
        try:
            await self.mongo_db.questionnaire_states.delete_one({"user_id": user_id})
            return True
        except Exception as e:
            logger.error(f"Error deleting user state from MongoDB: {e}")
            return False

    async def get_user_state(self, user_id: str) -> Dict[str, Any]:
        cache_key = get_questionnaire_cache_key(user_id)
        cached_state = get_cache(cache_key)
        if cached_state:
            cached_state['queue'] = deque(cached_state.get('queue', []))
            logger.debug(f"Using cached state for user {user_id}")
            return cached_state
            
        db_state = await self._get_user_state_from_db(user_id)
        if db_state:
            set_cache(cache_key, db_state)
            return db_state
            
        initial_state = self._create_initial_state()
        await self._update_user_state_in_db(user_id, initial_state)
        set_cache(cache_key, initial_state)
        return initial_state
        
    def _create_initial_state(self) -> Dict[str, Any]:
        if not self.basic_information_questions:
            logger.error("No basic information questions available to initialize state")
            self._create_default_questions()
        
        basic_q_ids = [q['id'] for q in self.basic_information_questions.values()]
        queue = deque(basic_q_ids)
        logger.info(f"Created initial queue with {len(queue)} questions: {basic_q_ids}")
        
        return {
            'queue': queue, 'answers': {}, 'answered_questions': [],
            'participating_questions_count': self.total_questions,
            'version': self.current_version, 'start_time': time.time()
        }
        
    async def update_user_state(self, user_id: str, state: Dict[str, Any]) -> bool:
        cache_key = get_questionnaire_cache_key(user_id)
        cache_updated = set_cache(cache_key, state)
        db_updated = await self._update_user_state_in_db(user_id, state)
        return cache_updated or db_updated
        
    async def get_next_question(self, user_id: str, new_answers: Dict[str, Any] = None) -> Tuple[Optional[Dict[str, Any]], bool, bool]:
        state = await self.get_user_state(user_id)
        is_user_chose_to_continue = False
        
        if new_answers:
            for q_id, answer_val in new_answers.items():
                if q_id == CONTINUATION_PROMPT_ID:
                    is_user_chose_to_continue = True
                    continue
                if q_id not in state['answered_questions']:
                    state['answers'][q_id] = answer_val
                    state['answered_questions'].append(q_id)
                    self._update_queue_based_on_answer(state, q_id, answer_val)
        
        self._add_follow_up_questions_to_queue(state)

        await self.update_user_state(user_id, state)
        
        next_question_data = await self._get_next_question_from_queue(state, user_id)
        if next_question_data:
            return next_question_data, False, is_user_chose_to_continue
        
        questions_added = await self._populate_question_queue_if_needed(state, user_id)
        if questions_added:
            return await self.get_next_question(user_id)
        
        return None, True, is_user_chose_to_continue

    async def _populate_question_queue_if_needed(self, state: Dict[str, Any], user_id: str) -> bool:
        answered_count = len(state['answered_questions'])
        if answered_count < 10:
            return await self._populate_initial_batch(state, user_id, answered_count)
        else:
            return await self._populate_subsequent_batch(state, user_id)

    async def _populate_initial_batch(self, state: Dict[str, Any], user_id: str, answered_count: int) -> bool:
        if not state['queue']:
            basic_q_ids = list(self.basic_information_questions.keys())
            unanswered_basic = self._get_unanswered_questions(state, basic_q_ids)
            if unanswered_basic:
                state['queue'].extend([q_id for q_id in basic_q_ids if q_id in unanswered_basic])
                await self.update_user_state(user_id, state)
                if state['queue']: return True
            
            if answered_count + len(state['queue']) < 10:
                needed_count = 10 - (answered_count + len(state['queue']))
                dynamic_q_ids = list(self.dynamic_questionnaire.keys())
                unanswered_dynamic = self._get_unanswered_questions(state, dynamic_q_ids)
                location_questions = self._get_location_convenience_questions(unanswered_dynamic)
                questions_to_add = location_questions[:needed_count]
                if questions_to_add:
                    state['queue'].extend(questions_to_add)
                    await self.update_user_state(user_id, state)
                    if state['queue']: return True
        return False

    async def _populate_subsequent_batch(self, state: Dict[str, Any], user_id: str) -> bool:
        if not state['queue']:
            all_q_ids = list(self.basic_information_questions.keys()) + list(self.dynamic_questionnaire.keys())
            unanswered = [q_id for q_id in all_q_ids if q_id not in state['answered_questions']]
            if unanswered:
                location_questions = self._get_location_convenience_questions(unanswered)
                next_batch = location_questions[:5]
                if next_batch:
                    state['queue'].extend(next_batch)
                    await self.update_user_state(user_id, state)
                    if state['queue']: return True
        return False

    def _add_follow_up_questions_to_queue(self, state: Dict[str, Any]) -> None:
        last_answered_question = state['answered_questions'][-1] if state['answered_questions'] else None
        if not last_answered_question:
            return

        last_answer_val = state['answers'].get(last_answered_question)
        graph_node = self.question_graph.get(last_answered_question, {})
        follow_up_id = None

        if graph_node.get('on_answered') and last_answer_val:
            follow_up_id = graph_node['on_answered'].get('id')
        elif graph_node.get('on_unanswered') and not last_answer_val:
            follow_up_id = graph_node['on_unanswered'].get('id')

        if follow_up_id and follow_up_id not in state['queue']:
            state['queue'].appendleft(follow_up_id)
            logger.info(f"Added follow-up question '{follow_up_id}' to the front of the queue.")
    
    async def _get_next_question_from_queue(self, state: Dict[str, Any], user_id: str) -> Optional[Dict[str, Any]]:
        if not state['queue']: return None
        next_q_id = state['queue'].popleft()
        await self.update_user_state(user_id, state)
        
        all_questions = {**self.basic_information_questions, **self.dynamic_questionnaire}
        
        question_data = all_questions.get(next_q_id)
        if question_data: 
            return question_data
        
        for q_data_node in self.question_graph.values():
            if q_data_node.get('on_unanswered', {}).get('id') == next_q_id: 
                return q_data_node['on_unanswered']
            if q_data_node.get('on_answered', {}).get('id') == next_q_id: 
                return q_data_node['on_answered']
        return None

    def get_basic_questions_length(self) -> int:
        return len(self.basic_information_questions)

    def _get_unanswered_questions(self, state: Dict[str, Any], question_ids: List[str]) -> List[str]:
        return [q_id for q_id in question_ids if q_id not in state['answered_questions'] and q_id not in state['queue']]

    def _get_location_convenience_questions(self, question_ids: List[str]) -> List[str]:
        return [q_id for q_id in question_ids if q_id in self.dynamic_questionnaire and self.dynamic_questionnaire[q_id].get('category') == 'Location and Convenience']

    def _update_queue_based_on_answer(self, state: Dict[str, Any], question_id: str, answer: Any) -> None:
        """
        Update the question queue based on a user's answer, parsing JSON strings first.
        """
        parsed_answer = answer
        # Check if the answer is a string that looks like a list/JSON array
        if isinstance(answer, str) and answer.startswith('[') and answer.endswith(']'):
            try:
                # Attempt to parse it into a Python list
                parsed_answer = json.loads(answer)
                # Update the answer in the state so it's stored correctly
                state['answers'][question_id] = parsed_answer
                logger.debug(f"Successfully parsed string answer to list for question {question_id}.")
            except json.JSONDecodeError:
                logger.warning(f"Could not parse string-like-list answer for question {question_id}. Treating as string.")
        
        if question_id in self.question_graph:
            branch_questions = self._get_branch_questions(question_id, parsed_answer)
            self._add_questions_to_queue(state, branch_questions)

    def _get_branch_questions(self, question_id: str, answer: Any) -> List[str]:
        if question_id not in self.question_graph: return []
        answers_to_check = answer if isinstance(answer, list) else [answer]
        branch_questions = set()
        branches = self.question_graph[question_id].get('branches', {})
        for single_answer in answers_to_check:
            if single_answer in branches:
                branch_result = branches[single_answer]
                if isinstance(branch_result, list):
                    branch_questions.update(branch_result)
                else:
                    branch_questions.add(branch_result)
        return list(branch_questions)

    def _add_questions_to_queue(self, state: Dict[str, Any], questions: List[str]) -> None:
        for q_id in questions:
            if q_id and q_id not in state['answered_questions'] and q_id not in state['queue']:
                state['queue'].append(q_id)
                self.added_participating_questions_count += 1

    async def save_completed_questionnaire(self, user_id: str) -> bool:
        if self.mongo_db is None: return False
        state = await self.get_user_state(user_id)
        if not state.get('answers'):
            logger.warning(f"Attempted to save empty questionnaire for user {user_id}")
            return False

        try:
            completed_doc = {
                "user_id": user_id,
                "answers": state['answers'],
                "questionnaire_version": state['version'],
                "submitted_at": datetime.now(timezone.utc),
                "question_count": len(state['answered_questions']),
            }
            await self.mongo_db.completed_questionnaires.insert_one(completed_doc)
            
            await self._delete_user_state_from_db(user_id)
            delete_cache(get_questionnaire_cache_key(user_id))
            return True
        except Exception as e:
            logger.error(f"Error saving completed questionnaire to MongoDB: {e}")
            return False

    async def get_completed_questionnaire(self, user_id: str) -> Optional[Dict[str, Any]]:
        if self.mongo_db is None:
            return None
        return await self.mongo_db.completed_questionnaires.find_one({"user_id": user_id})

    def _create_default_questions(self) -> None:
        logger.warning("Creating default questions as fallback")
        self.basic_information_questions = {
            "default_question": {"id": "default_question", "text": "Default question", "type": "text"}
        }
        self.dynamic_questionnaire = {}