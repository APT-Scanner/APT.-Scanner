"""Service for managing questionnaires and user responses."""
import json
import logging
import numpy as np
import random
from typing import Dict, Any, List, Optional, Tuple
from collections import deque
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import time
from ..utils.cache.redis_client import (
    get_cache, set_cache, delete_cache, get_questionnaire_cache_key
)
from ..config.constant import CONTINUATION_PROMPT_ID
from ..database.mongo_db import get_mongo_db
from ..database.models import UserPreferenceVector
from ..database.schemas import UserFiltersCreate, UserFiltersUpdate
from . import filters_service

logger = logging.getLogger(__name__)

class QuestionnaireService:
    """Service for managing questionnaires and user responses."""
    
    def __init__(self, db_session: AsyncSession = None):
        """
        Initialize the questionnaire service.
        
        Args:
            db_session: SQLAlchemy async session for database access (can be None)
        """
        self.db_session = db_session 
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
        
        return graph

    def _build_node_recursively(self, graph: Dict, question_data: Dict):
        """
        Recursively builds a node for a question and any questions nested inside it.
        """
        q_id = question_data.get('id')
        if not q_id or q_id in graph:
            return

        graph[q_id] = self._create_graph_node()
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

    def _create_graph_node(self) -> Dict[str, Any]:
        """Helper to create a standard graph node structure."""
        return {"branches": {}, "on_answered": {}, "on_unanswered": {}}

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
            # Migrate existing states to include current_question_id
            if 'current_question_id' not in cached_state:
                cached_state['current_question_id'] = None
            logger.debug(f"Using cached state for user {user_id}")
            return cached_state
            
        db_state = await self._get_user_state_from_db(user_id)
        if db_state:
            # Migrate existing states to include current_question_id
            if 'current_question_id' not in db_state:
                db_state['current_question_id'] = None
            set_cache(cache_key, db_state)
            return db_state
        
        # Check if user has a completed questionnaire but no active state
        completed_questionnaire = await self.get_completed_questionnaire(user_id)
        if completed_questionnaire:
            logger.info(f"User {user_id} has completed questionnaire, creating state with answered questions")
            initial_state = self._create_initial_state()
            # Populate answered questions from completed questionnaire
            initial_state['answers'] = completed_questionnaire.get('answers', {})
            initial_state['answered_questions'] = list(completed_questionnaire.get('answers', {}).keys())
            initial_state['version'] = completed_questionnaire.get('questionnaire_version', self.current_version)
            await self._update_user_state_in_db(user_id, initial_state)
            set_cache(cache_key, initial_state)
            return initial_state
            
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
            'current_question_id': None,  # Track current question without removing from queue
            'participating_questions_count': self.total_questions,
            'version': self.current_version, 'start_time': time.time()
        }
        
    async def update_user_state(self, user_id: str, state: Dict[str, Any]) -> bool:
        cache_key = get_questionnaire_cache_key(user_id)
        cache_updated = set_cache(cache_key, state)
        db_updated = await self._update_user_state_in_db(user_id, state)
        return cache_updated or db_updated
        
    async def get_next_question_internal(self, user_id: str, new_answers: Dict[str, Any] = None) -> Tuple[Optional[Dict[str, Any]], bool, bool]:
        state = await self.get_user_state(user_id)
        is_user_chose_to_continue = False
        
        if new_answers:
            for q_id, answer_val in new_answers.items():
                if q_id == CONTINUATION_PROMPT_ID:
                    is_user_chose_to_continue = True
                    continue
                
                # Always update the answer (allows changing answers to previously answered questions)
                state['answers'][q_id] = answer_val
                
                # Only add to answered_questions if not already there
                if q_id not in state['answered_questions']:
                    state['answered_questions'].append(q_id)
                
                self._update_queue_based_on_answer(state, q_id, answer_val)
                
                # Remove the answered question from queue if it's the current one
                if state.get('current_question_id') == q_id and state['queue'] and state['queue'][0] == q_id:
                    state['queue'].popleft()
                    state['current_question_id'] = None
        
        self._add_follow_up_questions_to_queue(state)

        await self.update_user_state(user_id, state)
        
        next_question_data = await self._get_next_question_from_queue(state, user_id)
        if next_question_data:
            return next_question_data, False, is_user_chose_to_continue
        
        questions_added = await self._populate_question_queue_if_needed(state, user_id)
        if questions_added:
            return await self.get_next_question_internal(user_id)
        
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
        if not state['queue']: 
            return None
            
        # If we already have a current question and it hasn't been answered, return it
        current_q_id = state.get('current_question_id')
        if current_q_id and current_q_id not in state['answered_questions']:
            all_questions = {**self.basic_information_questions, **self.dynamic_questionnaire}
            question_data = all_questions.get(current_q_id)
            if question_data:
                return question_data
                
            # Check in conditional questions
            for q_data_node in self.question_graph.values():
                if q_data_node.get('on_unanswered', {}).get('id') == current_q_id: 
                    return q_data_node['on_unanswered']
                if q_data_node.get('on_answered', {}).get('id') == current_q_id: 
                    return q_data_node['on_answered']
        
        # Get the next question from queue without removing it
        next_q_id = state['queue'][0]
        state['current_question_id'] = next_q_id
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

    def get_basic_questions_count(self) -> int:
        return len(self.basic_information_questions)

    def _get_unanswered_questions(self, state: Dict[str, Any], question_ids: List[str]) -> List[str]:
        return [q_id for q_id in question_ids if q_id not in state['answered_questions'] and q_id not in state['queue']]

    def _get_location_convenience_questions(self, question_ids: List[str]) -> List[str]:
        location_questions = [q_id for q_id in question_ids if q_id in self.dynamic_questionnaire and self.dynamic_questionnaire[q_id].get('category') == 'Location and Convenience']
        # Randomize the order of Location and Convenience questions
        random.shuffle(location_questions)
        logger.debug(f"Randomized {len(location_questions)} Location and Convenience questions: {location_questions}")
        return location_questions

    def _update_queue_based_on_answer(self, state: Dict[str, Any], question_id: str, answer: Any) -> None:
        """
        Update the question queue based on a user's answer, parsing JSON strings first.
        """
        parsed_answer = answer
        
        # Special handling for POI questions - keep as JSON string for backend processing
        if question_id == 'points_of_interest':
            # Don't parse POI data for branching logic, keep as string
            logger.debug(f"POI question answered, keeping as JSON string for question {question_id}.")
        elif isinstance(answer, str) and answer.startswith('[') and answer.endswith(']'):
            try:
                # Attempt to parse it into a Python list for other question types
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
            # Skip complex data types (like dictionaries) that can't be used as dictionary keys
            if isinstance(single_answer, (dict, list)):
                continue
            # Convert answer to string for lookup if it's not already hashable
            try:
                if single_answer in branches:
                    branch_result = branches[single_answer]
                    if isinstance(branch_result, list):
                        branch_questions.update(branch_result)
                    else:
                        branch_questions.add(branch_result)
            except TypeError:
                # Skip unhashable types
                continue
        return list(branch_questions)

    def _add_questions_to_queue(self, state: Dict[str, Any], questions: List[str]) -> None:
        for q_id in questions:
            if q_id and q_id not in state['answered_questions'] and q_id not in state['queue']:
                state['queue'].append(q_id)
                self.added_participating_questions_count += 1

    async def save_completed_questionnaire(self, user_id: str) -> bool:
        if self.mongo_db is None: 
            return False
            
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
            
            # Calculate and save user preference vector to PostgreSQL
            if self.db_session:
                await self._save_user_preference_vector(user_id, state['answers'], state['version'])
                # Create or update user filters based on questionnaire answers
                await self._create_or_update_user_filters(user_id, state['answers'])
            
            await self._delete_user_state_from_db(user_id)
            delete_cache(get_questionnaire_cache_key(user_id))
            return True
        except Exception as e:
            logger.error(f"Error saving completed questionnaire to MongoDB: {e}")
            return False

    async def _save_user_preference_vector(self, user_id: str, user_responses: Dict[str, Any], version: int) -> bool:
        """Calculate and save user preference vector to PostgreSQL."""
        try:
            # Calculate preference vector using the same logic as recommendation service
            preference_vector = self._calculate_preference_vector(user_responses)
            
            # Create or update user preference vector record
            existing = await self.db_session.execute(
                select(UserPreferenceVector).where(UserPreferenceVector.user_id == user_id)
            )
            existing_record = existing.scalar_one_or_none()
            
            if existing_record:
                # Update existing record
                existing_record.cultural_level = preference_vector[0]
                existing_record.religiosity_level = preference_vector[1]
                existing_record.communality_level = preference_vector[2]
                existing_record.kindergardens_level = preference_vector[3]
                existing_record.maintenance_level = preference_vector[4]
                existing_record.mobility_level = preference_vector[5]
                existing_record.parks_level = preference_vector[6]
                existing_record.peaceful_level = preference_vector[7]
                existing_record.shopping_level = preference_vector[8]
                existing_record.safety_level = preference_vector[9]
                existing_record.nightlife_level = preference_vector[10]  # Added nightlife level
                existing_record.preference_vector = preference_vector.tolist()
                existing_record.questionnaire_version = version
                existing_record.updated_at = datetime.now(timezone.utc)
            else:
                # Create new record
                user_pref_vector = UserPreferenceVector(
                    user_id=user_id,
                    cultural_level=preference_vector[0],
                    religiosity_level=preference_vector[1],
                    communality_level=preference_vector[2],
                    kindergardens_level=preference_vector[3],
                    maintenance_level=preference_vector[4],
                    mobility_level=preference_vector[5],
                    parks_level=preference_vector[6],
                    peaceful_level=preference_vector[7],
                    shopping_level=preference_vector[8],
                    safety_level=preference_vector[9],
                    nightlife_level=preference_vector[10],  # Added nightlife level
                    preference_vector=preference_vector.tolist(),
                    questionnaire_version=version,
                    updated_at=datetime.now(timezone.utc)
                )
                self.db_session.add(user_pref_vector)
            
            await self.db_session.commit()
            logger.info(f"Successfully saved preference vector for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving preference vector for user {user_id}: {e}", exc_info=True)
            await self.db_session.rollback()
            return False

    def _calculate_preference_vector(self, responses: Dict[str, Any]) -> np.ndarray:
        """
        Calculate user preference vector from questionnaire responses.
        Uses the same logic as the recommendation service.
        """
        # Feature names in order (matching NeighborhoodFeatures)
        feature_names = [
            'cultural_level',           # 0
            'religiosity_level',        # 1  
            'communality_level',        # 2
            'kindergardens_level',      # 3
            'maintenance_level',        # 4
            'mobility_level',           # 5
            'parks_level',              # 6
            'peaceful_level',           # 7
            'shopping_level',           # 8
            'safety_level',             # 9
            'nightlife_level'           # 10 - Added nightlife level
        ]
        
        # Importance scale mapping
        importance_scale = {
            'Very important': 0.9,
            'Somewhat important': 0.6,
            'Not important': 0.1,
            'Yes, I want to be in the center of the action': 0.9,
            'Close but not too close': 0.6,
            'As far as possible': 0.1,
            'No preference': 0.5,
            'Walking distance': 0.9,
            'Short drive or public transport ride': 0.6,
            'Very important - I want well-maintained buildings': 0.9,
            'Not important - I don\'t mind older/less maintained areas': 0.1,
            'Very important - I need a quiet area': 0.9,
            'Not important - I don\'t mind noise': 0.1,
            'Very important - I want an active, connected community': 0.9,
            'Not important - I prefer privacy': 0.2,
            'No': 0.1,
            'Yes': 0.9
        }
        
        preferences = {feature: 0.5 for feature in feature_names}  # Default neutral
        
        # Apply mapping logic
        self._map_basic_questions(responses, preferences, importance_scale)
        self._map_dynamic_questions(responses, preferences, importance_scale)
        self._apply_persona_logic(responses, preferences)
        
        # Convert to array
        preference_vector = np.array([preferences[feature] for feature in feature_names])
        return preference_vector

    def _map_basic_questions(self, responses: Dict, preferences: Dict, importance_scale: Dict):
        """Map basic information questions."""
        if 'religious_community_importance' in responses:
            importance = importance_scale.get(responses['religious_community_importance'], 0.5)
            preferences['religiosity_level'] = importance
        
        if 'safety_priority' in responses:
            importance = importance_scale.get(responses['safety_priority'], 0.5)
            preferences['safety_level'] = importance
        
        if 'commute_pref' in responses:
            commute_type = responses['commute_pref']
            if commute_type in ['Public transport', 'Walking']:
                preferences['mobility_level'] = 0.8
            elif commute_type in ['Bicycle / scooter']:
                preferences['mobility_level'] = 0.7
            elif commute_type == 'Private car':
                preferences['mobility_level'] = 0.4

    def _map_dynamic_questions(self, responses: Dict, preferences: Dict, importance_scale: Dict):
        """Map dynamic questionnaire questions."""
        # Children ages -> affects multiple features
        if 'children_ages' in responses:
            children_ages = responses['children_ages']
            if isinstance(children_ages, list):
                children_ages = children_ages[0] if children_ages else 'No children'
            
            if 'No children' not in children_ages:
                preferences['safety_level'] = max(preferences['safety_level'], 0.8)
                preferences['kindergardens_level'] = max(preferences['kindergardens_level'], 0.7)
                preferences['peaceful_level'] = max(preferences['peaceful_level'], 0.7)
        
        # Learning spaces -> cultural_level
        if 'learning_space_nearby' in responses:
            importance = importance_scale.get(responses['learning_space_nearby'], 0.5)
            preferences['cultural_level'] = max(preferences['cultural_level'], importance)
        
        # Shopping centers -> shopping_level
        if 'proximity_to_shopping_centers' in responses:
            importance = importance_scale.get(responses['proximity_to_shopping_centers'], 0.5)
            preferences['shopping_level'] = importance
        
        # Green spaces -> parks_level
        if 'proximity_to_green_spaces' in responses:
            importance = importance_scale.get(responses['proximity_to_green_spaces'], 0.5)
            preferences['parks_level'] = importance
        
        # Family activities -> communality_level
        if 'family_activities_nearby' in responses:
            importance = importance_scale.get(responses['family_activities_nearby'], 0.5)
            preferences['communality_level'] = max(preferences['communality_level'], importance)
        
        # Nightlife -> nightlife_level and peaceful_level (inverse)
        if 'nightlife_proximity' in responses:
            response = responses['nightlife_proximity']
            if response == 'Yes, I want to be in the center of the action':
                preferences['nightlife_level'] = max(preferences['nightlife_level'], 0.9)
                preferences['cultural_level'] = max(preferences['cultural_level'], 0.9)
                preferences['peaceful_level'] = min(preferences['peaceful_level'], 0.3)
            elif response == 'Close but not too close':
                preferences['nightlife_level'] = max(preferences['nightlife_level'], 0.6)
                preferences['cultural_level'] = max(preferences['cultural_level'], 0.6)
                preferences['peaceful_level'] = 0.6
            elif response == 'As far as possible':
                preferences['nightlife_level'] = min(preferences['nightlife_level'], 0.2)
                preferences['cultural_level'] = min(preferences['cultural_level'], 0.2)
                preferences['peaceful_level'] = max(preferences['peaceful_level'], 0.9)
        
        # Community involvement -> communality_level
        if 'community_involvement_preference' in responses:
            importance = importance_scale.get(responses['community_involvement_preference'], 0.5)
            preferences['communality_level'] = max(preferences['communality_level'], importance)
        
        # Cultural activities -> cultural_level
        if 'cultural_activities_importance' in responses:
            importance = importance_scale.get(responses['cultural_activities_importance'], 0.5)
            preferences['cultural_level'] = max(preferences['cultural_level'], importance)
        
        # Neighborhood quality -> maintenance_level
        if 'neighborhood_quality_importance' in responses:
            importance = importance_scale.get(responses['neighborhood_quality_importance'], 0.5)
            preferences['maintenance_level'] = importance
        
        # Building condition -> maintenance_level
        if 'building_condition_preference' in responses:
            importance = importance_scale.get(responses['building_condition_preference'], 0.5)
            preferences['maintenance_level'] = max(preferences['maintenance_level'], importance)
        
        # Quiet hours -> peaceful_level
        if 'quiet_hours_importance' in responses:
            importance = importance_scale.get(responses['quiet_hours_importance'], 0.5)
            preferences['peaceful_level'] = max(preferences['peaceful_level'], importance)
        
        # Pet ownership -> parks_level
        if 'pet_ownership' in responses:
            if responses['pet_ownership'] == 'Yes':
                preferences['parks_level'] = max(preferences['parks_level'], 0.7)

    def _apply_persona_logic(self, responses: Dict, preferences: Dict):
        """Apply logic based on housing purpose (user persona)."""
        if 'housing_purpose' not in responses:
            return
        
        housing_purpose = responses['housing_purpose']
        if isinstance(housing_purpose, list):
            housing_purpose = housing_purpose[0] if housing_purpose else ''
        
        # Adjust preferences based on persona
        if 'Just me' in housing_purpose:
            preferences['cultural_level'] = max(preferences['cultural_level'], 0.6)
            preferences['shopping_level'] = max(preferences['shopping_level'], 0.6)
            preferences['mobility_level'] = max(preferences['mobility_level'], 0.6)
            preferences['nightlife_level'] = max(preferences['nightlife_level'], 0.6)
            
        elif 'With a partner' in housing_purpose:
            preferences['cultural_level'] = max(preferences['cultural_level'], 0.6)
            preferences['peaceful_level'] = max(preferences['peaceful_level'], 0.6)
            preferences['shopping_level'] = max(preferences['shopping_level'], 0.6)
            
        elif 'With family (and children)' in housing_purpose:
            preferences['safety_level'] = max(preferences['safety_level'], 0.8)
            preferences['kindergardens_level'] = max(preferences['kindergardens_level'], 0.7)
            preferences['parks_level'] = max(preferences['parks_level'], 0.7)
            preferences['peaceful_level'] = max(preferences['peaceful_level'], 0.7)
            preferences['communality_level'] = max(preferences['communality_level'], 0.6)
            preferences['nightlife_level'] = min(preferences['nightlife_level'], 0.3)  # Families typically avoid nightlife areas
            
        elif 'With roommates' in housing_purpose:
            preferences['cultural_level'] = max(preferences['cultural_level'], 0.7)
            preferences['shopping_level'] = max(preferences['shopping_level'], 0.6)
            preferences['mobility_level'] = max(preferences['mobility_level'], 0.7)
            preferences['nightlife_level'] = max(preferences['nightlife_level'], 0.7)

    async def get_completed_questionnaire(self, user_id: str) -> Optional[Dict[str, Any]]:
        if self.mongo_db is None:
            return None
        return await self.mongo_db.completed_questionnaires.find_one({"user_id": user_id})

    async def go_back_to_previous_question(self, user_id: str) -> Dict[str, Any]:
        """
        Remove the last answered question and return to the previous one.
        
        Args:
            user_id: User's Firebase UID
            
        Returns:
            Dictionary with question data or error
        """
        try:
            user_state = await self.get_user_state(user_id)
            answered_questions = user_state.get('answered_questions', [])
            
            # Cannot go back if no questions were answered
            if not answered_questions:
                logger.warning(f"User {user_id} attempted to go back but no questions were answered")
                return {
                    "error": "No previous questions to go back to",
                    "question": None,
                    "is_complete": False
                }
            
            # Get the last answered question ID
            last_question_id = answered_questions[-1]
            logger.info(f"User {user_id} going back from question {last_question_id}")
            
            # Remove the last question from answered questions (but keep the answer)
            user_state['answered_questions'] = answered_questions[:-1]
            
            # DON'T remove the answer - keep it so it can be displayed and edited
            # The answer will remain in user_state['answers'][last_question_id]
            
            # Update queue to include the removed question at the front
            if 'queue' not in user_state:
                user_state['queue'] = deque()
            user_state['queue'].appendleft(last_question_id)
            
            # Save updated state
            success = await self.update_user_state(user_id, user_state)
            if not success:
                logger.error(f"Failed to update user state when going back for user {user_id}")
                return {
                    "error": "Failed to update questionnaire state",
                    "question": None,
                    "is_complete": False
                }
            
            # Now get the current question (which should be the previous one)
            return await self.start_questionnaire(user_id)
            
        except Exception as e:
            logger.error(f"Error going back to previous question for user {user_id}: {e}", exc_info=True)
            return {
                "error": f"Failed to go back to previous question: {str(e)}",
                "question": None,
                "is_complete": False
            }

    async def get_user_responses(self, db: AsyncSession, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user's questionnaire responses for recommendation generation.
        
        First tries to get completed questionnaire from MongoDB.
        If not found, gets answers from current user state.
        
        Args:
            db: Database session (for future use if needed)
            user_id: User's Firebase UID
            
        Returns:
            Dictionary of user's answers or None if no responses found
        """
        try:
            # Try to get completed questionnaire first
            completed = await self.get_completed_questionnaire(user_id)
            if completed and 'answers' in completed:
                logger.info(f"Found completed questionnaire for user {user_id}")
                return completed['answers']
            
            # Fallback to current user state if no completed questionnaire
            user_state = await self.get_user_state(user_id)
            if user_state and 'answers' in user_state and user_state['answers']:
                logger.info(f"Using current answers from user state for user {user_id}")
                return user_state['answers']
            
            logger.warning(f"No questionnaire responses found for user {user_id}")
            return None
            
        except Exception as e:
            logger.error(f"Error getting user responses for {user_id}: {e}", exc_info=True)
            return None

    async def skip_current_question_internal(self, user_id: str) -> bool:
        """
        Skip the current question by removing it from the queue and clearing current_question_id.
        Returns True if a question was skipped, False otherwise.
        """
        state = await self.get_user_state(user_id)
        current_q_id = state.get('current_question_id')
        
        if current_q_id and state['queue'] and state['queue'][0] == current_q_id:
            # Remove the question from queue and clear current question
            state['queue'].popleft()
            state['current_question_id'] = None
            await self.update_user_state(user_id, state)
            logger.info(f"Skipped question '{current_q_id}' for user {user_id}")
            return True
        
        return False

    def _create_default_questions(self) -> None:
        logger.warning("Creating default questions as fallback")
        self.basic_information_questions = {
            "default_question": {"id": "default_question", "text": "Default question", "type": "text"}
        }
        self.dynamic_questionnaire = {}

    
    COMPLETION_PROMPT = {
        "id": "final_completion_prompt",
        "text": "Congratulations! You've completed all the questions. Your preferences have been saved and we're ready to find the perfect apartments for you.",
        "type": "single-choice",
        "options": ["View matched apartments", "Start apartment swipe"],
        "category": "System",
        "display_type": "continuation_page"
    }

    async def calculate_questionnaire_progress(
        self, 
        user_state: Optional[Dict[str, Any]]
    ) -> Optional[float]:
        """Calculate the current progress of the questionnaire."""
        if not user_state:
            return 0.0

        answered_questions = user_state.get('answered_questions', [])
        num_answered = len(answered_questions)
        
        if num_answered <= 10:
            target_batch_size = 10
        else:
            additional_batches = (num_answered - 10 + 4) // 5  
            target_batch_size = 10 + (additional_batches * 5)
        
        total_questions = len(self.basic_information_questions) + len(self.dynamic_questionnaire)
        target_batch_size = min(target_batch_size, total_questions)
        
        if num_answered >= total_questions:
            return 100.0
        
        if target_batch_size > 0:
            progress = (num_answered / target_batch_size) * 100
            return round(min(progress, 100.0), 1)
        
        return 100.0

    def should_show_continuation_prompt(
        self, 
        user_state: Optional[Dict[str, Any]]
    ) -> bool:
        """Determine if a continuation prompt should be shown."""
        if not user_state:
            return False
            
        answered_questions = user_state.get('answered_questions', [])
        num_answered = len(answered_questions)

        if num_answered == 10 or (num_answered > 10 and (num_answered - 10) % 5 == 0):
            return True
        
        return False

    def should_show_final_prompt(
        self, 
        user_state: Optional[Dict[str, Any]]
    ) -> bool:
        """Determine if the final completion prompt should be shown."""
        if not user_state:
            return False
        
        answered_questions = user_state.get('answered_questions', [])
        queue = user_state.get('queue', [])
        
        all_question_ids = list(self.basic_information_questions.keys()) + list(self.dynamic_questionnaire.keys())
        
        all_answered = all(q_id in answered_questions for q_id in all_question_ids)
        
        return not queue and all_answered

    async def get_current_stage_counts(
        self, 
        user_state: Optional[Dict[str, Any]]
    ) -> Tuple[Optional[int], Optional[int]]:
        """Get the current stage question counts."""
        if not user_state:
            return None, None

        num_answered = len(user_state.get('answered_questions', []))
        participating_questions_count = user_state.get('participating_questions_count', 0)
        
        if num_answered < 10:
            return 10, num_answered
        else:
            current_batch_number = ((num_answered - 10) // 5) + 1
            batch_start = 10 + ((current_batch_number - 1) * 5)
            batch_end = min(batch_start + 5, participating_questions_count)
            questions_in_current_batch = min(num_answered - batch_start, 5)
            current_batch_size = batch_end - batch_start
            return current_batch_size, questions_in_current_batch

    async def start_questionnaire(self, user_id: str) -> Dict[str, Any]:
        """
        Start or resume questionnaire.
        Returns a complete response ready for the API endpoint.
        """
        user_state = await self.get_user_state(user_id)
        
        # Check if user is continuing with additional questions
        is_continuing_additional = user_state.get('continuing_additional', False)
        if is_continuing_additional:
            # Clear the flag after checking it
            user_state['continuing_additional'] = False
            await self.update_user_state(user_id, user_state)
            logger.info(f"User {user_id} continuing with additional questions, skipping continuation prompts")
        
        show_final = self.should_show_final_prompt(user_state)
        if show_final:
            progress = await self.calculate_questionnaire_progress(user_state)
            current_stage_total, current_stage_answered = await self.get_current_stage_counts(user_state)
            return {
                "question": self.COMPLETION_PROMPT,
                "is_complete": True,
                "progress": 100.0,
                "current_stage_total_questions": current_stage_total,
                "current_stage_answered_questions": current_stage_answered,
                "show_continuation_prompt": False
            }
        
        # Skip continuation prompt if user is continuing with additional questions
        show_prompt = self.should_show_continuation_prompt(user_state) and not is_continuing_additional
        if show_prompt and not show_final:
            progress = await self.calculate_questionnaire_progress(user_state)
            current_stage_total, current_stage_answered = await self.get_current_stage_counts(user_state)
            return {
                "question": None,
                "is_complete": False,
                "progress": progress,
                "current_stage_total_questions": current_stage_total,
                "current_stage_answered_questions": current_stage_answered,
                "show_continuation_prompt": True
            }
        
        next_question, is_complete, _ = await self.get_next_question_internal(user_id)
        
        if is_complete:
            return {
                "question": self.COMPLETION_PROMPT,
                "is_complete": True,
                "progress": 100.0,
                "current_stage_total_questions": 0,
                "current_stage_answered_questions": 0,
                "show_continuation_prompt": False
            }
        
        progress = await self.calculate_questionnaire_progress(user_state)
        current_stage_total, current_stage_answered = await self.get_current_stage_counts(user_state)
        
        return {
            "question": next_question,
            "is_complete": is_complete,
            "progress": progress,
            "current_stage_total_questions": current_stage_total,
            "current_stage_answered_questions": current_stage_answered,
            "show_continuation_prompt": False
        }

    async def submit_answers(self, user_id: str, answers: Dict[str, Any]) -> Dict[str, Any]:
        """
        Submit answers and get next question.
        Returns a complete response ready for the API endpoint.
        """
        next_question, is_complete, is_user_chose_to_continue = await self.get_next_question_internal(
            user_id, answers
        )
        
        user_state = await self.get_user_state(user_id)
        
        show_final = self.should_show_final_prompt(user_state)
        if show_final:
            progress = await self.calculate_questionnaire_progress(user_state)
            current_stage_total, current_stage_answered = await self.get_current_stage_counts(user_state)
            return {
                "question": self.COMPLETION_PROMPT,
                "is_complete": True,
                "progress": 100.0,
                "current_stage_total_questions": current_stage_total,
                "current_stage_answered_questions": current_stage_answered,
                "show_continuation_prompt": False
            }
        
        show_prompt = self.should_show_continuation_prompt(user_state)
        if show_prompt and not is_user_chose_to_continue:
            progress = await self.calculate_questionnaire_progress(user_state)
            current_stage_total, current_stage_answered = await self.get_current_stage_counts(user_state)
            return {
                "question": None,
                "is_complete": False,
                "progress": progress,
                "current_stage_total_questions": current_stage_total,
                "current_stage_answered_questions": current_stage_answered,
                "show_continuation_prompt": True
            }

        progress = await self.calculate_questionnaire_progress(user_state)
        current_stage_total, current_stage_answered = await self.get_current_stage_counts(user_state)
        
        if is_complete:
            return {
                "question": self.COMPLETION_PROMPT,
                "is_complete": True,
                "progress": 100.0,
                "current_stage_total_questions": current_stage_total,
                "current_stage_answered_questions": current_stage_answered,
                "show_continuation_prompt": False
            }

        return {
            "question": next_question,
            "is_complete": is_complete,
            "progress": progress,
            "current_stage_total_questions": current_stage_total,
            "current_stage_answered_questions": current_stage_answered,
            "show_continuation_prompt": False
        }

    async def skip_question(self, user_id: str) -> Dict[str, Any]:
        """
        Skip current question.
        Returns a complete response ready for the API endpoint.
        """
        # Skip the current question
        skipped = await self.skip_current_question_internal(user_id)
        if not skipped:
            logger.warning(f"No question to skip for user {user_id}")
        
        # Get the next question
        next_question, is_complete, _ = await self.get_next_question_internal(user_id)
        
        user_state = await self.get_user_state(user_id)
        
        # Check for completion or continuation prompts
        show_final = self.should_show_final_prompt(user_state)
        if show_final:
            progress = await self.calculate_questionnaire_progress(user_state)
            current_stage_total, current_stage_answered = await self.get_current_stage_counts(user_state)
            return {
                "question": self.COMPLETION_PROMPT,
                "is_complete": True,
                "progress": 100.0,
                "current_stage_total_questions": current_stage_total,
                "current_stage_answered_questions": current_stage_answered,
                "show_continuation_prompt": False
            }
        
        show_prompt = self.should_show_continuation_prompt(user_state)
        if show_prompt:
            progress = await self.calculate_questionnaire_progress(user_state)
            current_stage_total, current_stage_answered = await self.get_current_stage_counts(user_state)
            return {
                "question": None,
                "is_complete": False,
                "progress": progress,
                "current_stage_total_questions": current_stage_total,
                "current_stage_answered_questions": current_stage_answered,
                "show_continuation_prompt": True
            }

        progress = await self.calculate_questionnaire_progress(user_state)
        current_stage_total, current_stage_answered = await self.get_current_stage_counts(user_state)
        
        if is_complete:
            return {
                "question": self.COMPLETION_PROMPT,
                "is_complete": True,
                "progress": 100.0,
                "current_stage_total_questions": current_stage_total,
                "current_stage_answered_questions": current_stage_answered,
                "show_continuation_prompt": False
            }

        return {
            "question": next_question,
            "is_complete": is_complete,
            "progress": progress,
            "current_stage_total_questions": current_stage_total,
            "current_stage_answered_questions": current_stage_answered,
            "show_continuation_prompt": False
        }

    async def get_questionnaire_status(self, user_id: str) -> Dict[str, Any]:
        """
        Get questionnaire status.
        Returns a complete response ready for the API endpoint.
        """
        completed_questionnaire = await self.get_completed_questionnaire(user_id)
        
        if completed_questionnaire:
            logger.info(f"User {user_id} has a completed questionnaire in MongoDB")
            return {
                "is_complete": True,
                "questions_answered": completed_questionnaire.get("question_count", 0),
            }
        
        user_state = await self.get_user_state(user_id)
        progress = await self.calculate_questionnaire_progress(user_state)
        current_stage_total, current_stage_answered = await self.get_current_stage_counts(user_state)
        
        is_complete = (progress == 100.0 and not user_state.get('queue')) if progress is not None else False
        show_prompt = self.should_show_continuation_prompt(user_state)
        
        return {
            "is_complete": is_complete,
            "progress": progress,
            "questions_answered": len(user_state.get('answered_questions', [])),
            "questions_remaining": len(user_state.get('queue', [])),
            "current_stage_total_questions": current_stage_total,
            "current_stage_answered_questions": current_stage_answered,
            "show_continuation_prompt": show_prompt
        }

    async def reset_current_question(self, user_id: str) -> bool:
        """
        Reset the current_question_id and queue to ensure fresh start when answering more questions.
        This is useful when a user wants to continue answering unanswered questions
        without being stuck on a previously shown but unanswered question.
        """
        try:
            user_state = await self.get_user_state(user_id)
            
            # Clear the current question pointer
            user_state['current_question_id'] = None
            
            # Clear the question queue to force repopulation with unanswered questions
            user_state['queue'] = deque()
            
            # Add a flag to indicate user wants to continue with additional questions
            user_state['continuing_additional'] = True
            
            # Save the updated state
            success = await self.update_user_state(user_id, user_state)
            
            if success:
                logger.info(f"Reset current_question_id and queue for additional questions for user {user_id}")
            else:
                logger.error(f"Failed to reset current_question_id for user {user_id}")
                
            return success
            
        except Exception as e:
            logger.error(f"Error resetting current question for user {user_id}: {e}", exc_info=True)
            return False

    async def _create_or_update_user_filters(self, user_id: str, user_responses: Dict[str, Any]) -> bool:
        """
        Create or update user filters based on questionnaire responses.
        
        Args:
            user_id: User's Firebase UID
            user_responses: User's questionnaire answers
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Extract filter-relevant answers
            filter_options = []
            price_min = 500  # Default values
            price_max = 15000
            
            # Map budget_range to price filters
            if 'budget_range' in user_responses:
                budget = user_responses['budget_range']
                if isinstance(budget, list) and len(budget) >= 2:
                    # budget_range is an array [min, max]
                    price_min = int(budget[0])
                    price_max = int(budget[1])
                elif isinstance(budget, (int, float)):
                    # Fallback: single value represents max budget
                    price_max = int(budget)
                    price_min = int(budget * 0.5)
                elif isinstance(budget, str):
                    # Try to parse if it's a string representation
                    try:
                        budget_val = int(budget)
                        price_max = budget_val
                        price_min = int(budget_val * 0.5)
                    except ValueError:
                        logger.warning(f"Could not parse budget_range value: {budget}")
                        
                logger.info(f"Mapped budget_range {budget} to price_min={price_min}, price_max={price_max}")
            
            # Map accessibility_needs to Accessibility option
            if 'accessibility_needs' in user_responses:
                if user_responses['accessibility_needs'] == 'Yes':
                    filter_options.append('Accessibility')
                    logger.info(f"Added Accessibility to filter options")
            
            # Map pet_ownership to Pets option
            if 'pet_ownership' in user_responses:
                if user_responses['pet_ownership'] == 'Yes':
                    filter_options.append('Pets')
                    logger.info(f"Added Pets to filter options")

            if 'housing_purpose' in user_responses:
                if user_responses['housing_purpose'] == 'With roommates':
                    filter_options.append('For Partners')
                    logger.info(f"Added Roommates to filter options")

            # Create filter update data
            filter_data = UserFiltersUpdate(
                price_min=price_min,
                price_max=price_max,
                options=','.join(filter_options) if filter_options else None
            )
            
            # Update or create user filters
            await filters_service.update_user_filters(self.db_session, user_id, filter_data)
            
            logger.info(f"Successfully updated filters for user {user_id} from questionnaire responses")
            return True
            
        except Exception as e:
            logger.error(f"Error creating/updating user filters from questionnaire for user {user_id}: {e}", exc_info=True)
            return False