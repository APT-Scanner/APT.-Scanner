"""Service for managing questionnaires and user responses."""
import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from collections import deque
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import delete
import time
from ..models.models import QuestionnaireState, CompletedQuestionnaire
from ..utils.cache.redis_client import (
    get_cache, set_cache, delete_cache, get_questionnaire_cache_key
)
from ..config.constant import CONTINUATION_PROMPT_ID

logger = logging.getLogger(__name__)

class QuestionnaireService:
    """Service for managing questionnaires and user responses."""
    
    def __init__(self, db_session: AsyncSession = None):
        """
        Initialize the questionnaire service.
        
        Args:
            db_session: SQLAlchemy async session for database access
        """
        self.db_session = db_session
        self.basic_information_questions = {}
        self.dynamic_questionnaire = {}
        self.question_graph = {}
        self.current_version = 1
        self.total_questions = 0
        self.initial_participating_questions_count = 0
        self.added_participating_questions_count = 0
        
        # Load question data from files
        try:
            logger.info("Loading basic information questions...")
            with open('data/sources/basic_information_questions.json', 'r') as f:
                questions_data = json.load(f)
                if not questions_data:
                    logger.error("basic_information_questions.json file is empty")
                self.basic_information_questions = {q['id']: q for q in questions_data}
                logger.info(f"Loaded {len(self.basic_information_questions)} basic information questions")
                
            logger.info("Loading dynamic questionnaire questions...")
            with open('data/sources/dynamic_questionnaire.json', 'r') as f:
                questions_data = json.load(f)
                if not questions_data:
                    logger.error("dynamic_questionnaire.json file is empty")
                self.dynamic_questionnaire = {q['id']: q for q in questions_data}
                logger.info(f"Loaded {len(self.dynamic_questionnaire)} dynamic questions")
            
            # Build the question dependency graph
            self.question_graph = self._build_question_graph()
            logger.info(f"Built question graph with {len(self.question_graph)} entries")
        except FileNotFoundError as e:
            logger.error(f"Question file not found: {e}")
            self._create_default_questions()
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in question file: {e}")
            self._create_default_questions()
        except Exception as e:
            logger.error(f"Error loading questionnaire data: {e}")
            self._create_default_questions()
        
    def _build_question_graph(self) -> Dict[str, Dict[str, Any]]:
        """
        Builds a graph of questions and their dependencies.
        
        Returns:
            A dictionary mapping question IDs to their next questions and branches
        """
        graph = {}
        self.total_questions = 0  # Reset counter before building
        
        # Process basic information questions first
        self._process_basic_questions_for_graph(graph)
        
        # Process dynamic questionnaire questions
        self._process_dynamic_questions_for_graph(graph)
        
        logger.info(f"Total questions count: {self.total_questions}")
        return graph

    def _process_basic_questions_for_graph(self, graph: Dict[str, Dict[str, Any]]) -> None:
        """Process basic information questions for the graph."""
        start_questions = list(self.basic_information_questions.values())
        
        for index, question in enumerate(start_questions):
            next_question_id = start_questions[index + 1]['id'] if index < len(start_questions) - 1 else None
            
            # Create base graph node
            graph[question['id']] = self._create_graph_node(next_question_id)
            self.total_questions += 1
            self.initial_participating_questions_count += 1
            
            # Process question branches and conditional logic
            self._add_question_branches(graph, question)
            self._add_conditional_questions(graph, question)

    def _process_dynamic_questions_for_graph(self, graph: Dict[str, Dict[str, Any]]) -> None:
        """Process dynamic questionnaire questions for the graph."""
        for q_id, question in self.dynamic_questionnaire.items():
            graph[q_id] = self._create_graph_node([])
            self.total_questions += 1
            
            if question.get('category') == 'Location and Convenience':
                self.initial_participating_questions_count += 1
                
            self._add_question_branches(graph, question, q_id)

    def _create_graph_node(self, next_default) -> Dict[str, Any]:
        """Create a basic graph node structure."""
        return {
            "next_default": next_default,
            "branches": {},
            "on_answered": {},
            "on_unanswered": {}
        }

    def _add_question_branches(self, graph: Dict[str, Dict[str, Any]], question: Dict[str, Any], q_id: str = None) -> None:
        """Add branches to a question in the graph."""
        question_id = q_id or question['id']
        
        if question.get('branches'):
            for answer, next_questions_val in question['branches'].items():
                graph[question_id]['branches'][answer] = next_questions_val

    def _add_conditional_questions(self, graph: Dict[str, Dict[str, Any]], question: Dict[str, Any]) -> None:
        """Add on_answered and on_unanswered conditional questions."""
        question_id = question['id']
        
        if question.get('on_answered'):
            graph[question_id]['on_answered'] = question['on_answered']
            graph[question['on_answered']['id']] = question['on_answered']
            self.total_questions += 1
            
        if question.get('on_unanswered'):
            graph[question_id]['on_unanswered'] = question['on_unanswered']
            graph[question['on_unanswered']['id']] = question['on_unanswered']
            self.total_questions += 1
            
        if question.get('on_unanswered') or question.get('on_answered'):
            self.initial_participating_questions_count += 1
        
    async def _get_user_state_from_db(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the user's questionnaire state from the database.
        
        Args:
            user_id: The user's unique identifier
            
        Returns:
            User state as a dictionary or None if not found
        """
        if not self._validate_db_session():
            return None
            
        try:
            query = select(QuestionnaireState).where(QuestionnaireState.user_id == user_id)
            result = await self.db_session.execute(query)
            state_record = result.scalars().first()
            
            if not state_record:
                return None
                
            # Parse JSON fields
            state = {
                'answers': json.loads(state_record.answers),
                'answered_questions': json.loads(state_record.answered_questions),
                'participating_questions_count': state_record.participating_questions_count,
                'version': state_record.questionnaire_version,
                'created_at': state_record.created_at,
                'last_updated': state_record.last_updated
            }
            
            # Convert queue to deque for more efficient operations
            queue_list = json.loads(state_record.queue)
            state['queue'] = deque(queue_list)
            
            return state
        except Exception as e:
            logger.error(f"Error retrieving user state from DB: {e}")
            return None
            
    async def _update_user_state_in_db(self, user_id: str, state: Dict[str, Any]) -> bool:
        """
        Update the user's questionnaire state in the database.
        
        Args:
            user_id: The user's unique identifier
            state: The state to save
            
        Returns:
            True if successful, False otherwise
        """
        async def update_operation():
            # Check if record exists
            query = select(QuestionnaireState).where(QuestionnaireState.user_id == user_id)
            result = await self.db_session.execute(query)
            state_record = result.scalars().first()
             
            # Convert deque to list for JSON serialization
            queue_list = list(state['queue']) if isinstance(state['queue'], deque) else state['queue']
            
            if state_record:
                # Update existing record
                state_record.queue = json.dumps(queue_list)
                state_record.answers = json.dumps(state['answers'])
                state_record.answered_questions = json.dumps(state['answered_questions'])
                state_record.participating_questions_count += self.added_participating_questions_count
                state_record.questionnaire_version = self.current_version
                state_record.last_updated = datetime.utcnow()
            else:
                # Create new record
                state_record = QuestionnaireState(
                    user_id=user_id,
                    queue=json.dumps(queue_list),
                    answers=json.dumps(state['answers']),
                    answered_questions=json.dumps(state['answered_questions']),
                    participating_questions_count=self.initial_participating_questions_count + self.added_participating_questions_count,
                    questionnaire_version=self.current_version,
                    created_at=datetime.utcnow(),
                    last_updated=datetime.utcnow()
                )
                self.db_session.add(state_record)
                
        return await self._execute_db_operation("updating user state in DB", update_operation)
            
    async def _delete_user_state_from_db(self, user_id: str) -> bool:
        """
        Delete the user's questionnaire state from the database.
        
        Args:
            user_id: The user's unique identifier
            
        Returns:
            True if successful, False otherwise
        """
        async def delete_operation():
            # Delete state record
            query = delete(QuestionnaireState).where(QuestionnaireState.user_id == user_id)
            await self.db_session.execute(query)
            
        return await self._execute_db_operation("deleting user state from DB", delete_operation)
            
    async def get_user_state(self, user_id: str) -> Dict[str, Any]:
        """
        Get the user's questionnaire state from cache or database.
        
        Args:
            user_id: The user's unique identifier
            
        Returns:
            User state as a dictionary, or a new state if not found
        """
        # Try to get from cache first
        cache_key = get_questionnaire_cache_key(user_id)
        cached_state = get_cache(cache_key)
        
        if cached_state:
            logger.debug(f"Using cached state for user {user_id}")
            return cached_state
            
        # Try to get from database
        db_state = await self._get_user_state_from_db(user_id)
        
        if db_state:
            # Update cache
            set_cache(cache_key, db_state)
            return db_state
            
        # Create new state if not found
        initial_state = self._create_initial_state()
        
        # Save to database and cache
        await self._update_user_state_in_db(user_id, initial_state)
        set_cache(cache_key, initial_state)
        
        return initial_state
        
    def _create_initial_state(self) -> Dict[str, Any]:
        """
        Create an initial questionnaire state with basic information questions.
        
        Returns:
            New state dictionary
        """
        # Start with basic information questions
        if not self.basic_information_questions:
            logger.error("No basic information questions available to initialize state")
            # Attempt to reload the questions
            try:
                with open('data/sources/basic_information_questions.json', 'r') as f:
                    self.basic_information_questions = {q['id']: q for q in json.load(f)}
                logger.info(f"Reloaded {len(self.basic_information_questions)} basic information questions")
            except Exception as e:
                logger.error(f"Failed to reload questions: {e}")
                # Create default questions as last resort
                self._create_default_questions()
        
        # Get all basic question IDs and maintain original order
        basic_q_ids = []
        for question in list(self.basic_information_questions.values()):
            basic_q_ids.append(question['id'])

            
        queue = deque(basic_q_ids)
        logger.info(f"Created initial queue with {len(queue)} questions: {basic_q_ids}")
        
        return {
            'queue': queue,
            'answers': {},
            'answered_questions': [],
            'participating_questions_count': self.initial_participating_questions_count,
            'version': self.current_version,
            'start_time': time.time()
        }
        
    async def update_user_state(self, user_id: str, state: Dict[str, Any]) -> bool:
        """
        Update the user's questionnaire state in cache and database.
        
        Args:
            user_id: The user's unique identifier
            state: The state to save
            
        Returns:
            True if successful, False otherwise
        """
        # Update cache
        cache_key = get_questionnaire_cache_key(user_id)
        cache_updated = set_cache(cache_key, state)
        
        # Update database
        db_updated = await self._update_user_state_in_db(user_id, state)
        
        return cache_updated or db_updated
        
    async def get_next_question(self, user_id: str, new_answers: Dict[str, Any] = None) -> Tuple[Optional[Dict[str, Any]], bool]:
        """
        Get the next question for a user based on their current state and new answers.
        
        Args:
            user_id: The user's unique identifier
            new_answers: New answers to incorporate
            
        Returns:
            A tuple containing:
            - The next question data or None if completed
            - Boolean indicating if the questionnaire is complete
        """
        # Get current state
        state = await self.get_user_state(user_id)
        
        # Update state with new answers
        if new_answers:
            for q_id, answer_val in new_answers.items():
                if q_id == CONTINUATION_PROMPT_ID:
                    return None, False, True
                if q_id not in state['answered_questions']:
                    state['answers'][q_id] = answer_val
                    state['answered_questions'].append(q_id)                    
                    self._update_queue_based_on_answer(state, q_id, answer_val)            
        
        # Save updated state
        await self.update_user_state(user_id, state)
        
        # Handle special case logic for the next question
        next_question_data = self._add_follow_up_questions_to_queue(state)

        if next_question_data:
            await self.update_user_state(user_id, state)
            return next_question_data, False, False
        
        # Return the next question if available in the queue
        next_question_data = await self._get_next_question_from_queue(state, user_id)
        if next_question_data:
            return next_question_data, False, False
        
        # Check if we should add more questions based on answered count
        questions_added = await self._populate_question_queue_if_needed(state, user_id)
        if questions_added:
            return await self.get_next_question(user_id)
        
        # If we've reached this point, the questionnaire is complete
        return None, True, False

    async def _populate_question_queue_if_needed(self, state: Dict[str, Any], user_id: str) -> bool:
        """
        Populate the question queue with new questions based on the batching strategy.
        
        Args:
            state: Current user state
            user_id: The user's unique identifier
            
        Returns:
            Boolean indicating if questions were added to the queue
        """
        answered_count = len(state['answered_questions'])
        
        # For the first batch, ensure we have filled the queue with initial questions
        if answered_count < 10:
            return await self._populate_initial_batch(state, user_id, answered_count)
        else:
            return await self._populate_subsequent_batch(state, user_id)

    async def _populate_initial_batch(self, state: Dict[str, Any], user_id: str, answered_count: int) -> bool:
        """
        Populate the initial batch of up to 10 questions.
        """
        # Fill queue if it's empty for the first batch
        if not state['queue']:
            # Get remaining basic information questions first
            basic_q_ids = list(self.basic_information_questions.keys())
            unanswered_basic = self._get_unanswered_questions(state, basic_q_ids)
            
            if unanswered_basic:
                # Add remaining basic questions to queue (preserving original order)
                remaining_basic = []
                for q_id in basic_q_ids:
                    if q_id in unanswered_basic:
                        remaining_basic.append(q_id)
                
                state['queue'].extend(remaining_basic)
                await self.update_user_state(user_id, state)
                
                if state['queue']:
                    return True
            
            # If we still need more to reach 10, add location and convenience questions
            if answered_count + len(state['queue']) < 10:
                needed_count = 10 - (answered_count + len(state['queue']))
                
                # Find unanswered dynamic questions
                dynamic_q_ids = list(self.dynamic_questionnaire.keys())
                unanswered_dynamic = self._get_unanswered_questions(state, dynamic_q_ids)
                
                # Prioritize questions by category or other criteria (similar to original logic)
                location_questions = self._get_location_convenience_questions(unanswered_dynamic)
                
                # Add questions up to needed count
                questions_to_add = location_questions[:needed_count]
                
                if questions_to_add:
                    state['queue'].extend(questions_to_add)
                    await self.update_user_state(user_id, state)
                    
                    if state['queue']:
                        return True
        return False

    async def _populate_subsequent_batch(self, state: Dict[str, Any], user_id: str) -> bool:
        """
        Populate subsequent batches of 5 questions after the initial 10.
        """
        # We're beyond 10 questions, check if we need a new batch of 5
        # Only add new questions if queue is empty (current batch completed)
        if not state['queue']:
            # Find all unanswered questions
            all_q_ids = list(self.basic_information_questions.keys()) + list(self.dynamic_questionnaire.keys())
            unanswered = [q_id for q_id in all_q_ids 
                        if q_id not in state['answered_questions']]
            
            if unanswered:
                # Prefer questions by category or other criteria (similar to original logic)
                location_questions = self._get_location_convenience_questions(unanswered)
                
                # Add the next batch of 5 questions
                next_batch = location_questions[:5]
                
                if next_batch:
                    state['queue'].extend(next_batch)
                    await self.update_user_state(user_id, state)
                    
                    if state['queue']:
                        return True
        return False

    def _add_follow_up_questions_to_queue(self, state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Add follow-up questions (on_answered/on_unanswered) to the queue based on the user's answers.
        Returns True if a follow-up question was added, False otherwise.
        """
        next_question_data = None
        last_answered_question = state['answered_questions'][-1] if state['answered_questions'] else None
        last_answer_val = state['answers'][last_answered_question] if last_answered_question else None

        # Handle questions with specific on_answered/on_unanswered conditions
        if last_answered_question in self.question_graph and self.question_graph[last_answered_question].get('on_answered') != {} and last_answer_val:
            next_question_data = self.question_graph[last_answered_question].get('on_answered')
            if state['queue'] and next_question_data and state['queue'][0] != next_question_data['id']:
                state['queue'].appendleft(next_question_data['id'])
        elif last_answered_question in self.question_graph and self.question_graph[last_answered_question].get('on_unanswered') != {} and not last_answer_val:
            next_question_data = self.question_graph[last_answered_question].get('on_unanswered')
            if state['queue'] and next_question_data and state['queue'][0] != next_question_data['id']:
                state['queue'].appendleft(next_question_data['id'])
                return next_question_data
        return None
    
    async def _get_next_question_from_queue(self, state: Dict[str, Any], user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the next question from the queue.
        """
        if state['queue']:
            next_q_id = state['queue'].popleft()
            await self.update_user_state(user_id, state)
            
            if next_q_id in self.basic_information_questions:
                next_question_data = self.basic_information_questions[next_q_id]
            elif next_q_id in self.dynamic_questionnaire:
                next_question_data = self.dynamic_questionnaire[next_q_id]
            else:
                for q_id, question_data in self.question_graph.items():
                    if hasattr(question_data, 'get') and question_data.get('on_unanswered') and question_data['on_unanswered'].get('id') == next_q_id:
                        next_question_data = question_data['on_unanswered']
                    elif hasattr(question_data, 'get') and question_data.get('on_answered') and question_data['on_answered'].get('id') == next_q_id:
                        next_question_data = question_data['on_answered']
            return next_question_data
        return None
    

    def get_basic_questions_length(self) -> int:
        """
        Get the number of basic questions.
        """
        return len(self.basic_information_questions)

    def _validate_db_session(self) -> bool:
        """Validate that database session is available."""
        if not self.db_session:
            logger.error("Database session not available")
            return False
        return True

    async def _execute_db_operation(self, operation_name: str, operation_func) -> bool:
        """
        Execute a database operation with error handling.
        
        Args:
            operation_name: Name of the operation for logging
            operation_func: Function to execute
            
        Returns:
            True if successful, False otherwise
        """
        if not self._validate_db_session():
            return False
            
        try:
            await operation_func()
            await self.db_session.commit()
            return True
        except Exception as e:
            logger.error(f"Error {operation_name}: {e}")
            await self.db_session.rollback()
            return False

    def _get_unanswered_questions(self, state: Dict[str, Any], question_ids: List[str]) -> List[str]:
        """Get questions that haven't been answered or queued."""
        return [q_id for q_id in question_ids 
                if q_id not in state['answered_questions'] 
                and q_id not in state['queue']]

    def _get_location_convenience_questions(self, question_ids: List[str]) -> List[str]:
        """Filter questions by Location and Convenience category."""
        return [q_id for q_id in question_ids 
                if q_id in self.dynamic_questionnaire and 
                self.dynamic_questionnaire[q_id].get('category') == 'Location and Convenience']

    def _is_question_available_for_queue(self, q_id: str, answered: List[str], queue) -> bool:
        """Check if a question can be added to the queue."""
        return q_id and q_id not in answered and q_id not in queue

    def _update_queue_based_on_answer(self, state: Dict[str, Any], question_id: str, answer: Any) -> None:
        """
        Update the question queue based on a user's answer.
        
        Args:
            state: Current user state
            question_id: The ID of the answered question
            answer: The user's answer (could be a string, list, or JSON-encoded string)
        """
        # Parse JSON answer if needed
        parsed_answer = self._parse_answer_if_json(state, question_id, answer)
        
        # Remove answered question from queue
        self._remove_question_from_queue(state, question_id)
        
        # Process question branches based on type
        if question_id in self.basic_information_questions:
            self._process_basic_question_branches(state, question_id, parsed_answer)
        elif question_id in self.dynamic_questionnaire:
            self._process_dynamic_question_branches(state, question_id, parsed_answer)

    def _parse_answer_if_json(self, state: Dict[str, Any], question_id: str, answer: Any) -> Any:
        """Parse JSON string answers if needed."""
        if isinstance(answer, str) and answer.startswith('[') and answer.endswith(']'):
            try:
                parsed_answer = json.loads(answer)
                state['answers'][question_id] = parsed_answer
                logger.debug(f"Parsed JSON answer for question {question_id}: {parsed_answer}")
                return parsed_answer
            except json.JSONDecodeError:
                logger.debug(f"Received a string that looks like JSON but isn't: {answer}")
        return answer

    def _remove_question_from_queue(self, state: Dict[str, Any], question_id: str) -> None:
        """Remove the answered question from the queue."""
        queue = state['queue']
        if queue and queue[0] == question_id:
            queue.popleft()
        elif question_id in queue:
            queue_list = list(queue)
            queue_list.remove(question_id)
            state['queue'] = deque(queue_list)

    def _process_basic_question_branches(self, state: Dict[str, Any], question_id: str, answer: Any) -> None:
        """Process branching logic for basic information questions."""
        if question_id not in self.question_graph:
            return
            
        branch_questions = self._get_branch_questions(question_id, answer)
        self._add_questions_to_queue(state, branch_questions)

    def _process_dynamic_question_branches(self, state: Dict[str, Any], question_id: str, answer: Any) -> None:
        """Process branching logic for dynamic questionnaire questions."""
        next_questions = []
        
        if isinstance(answer, list):
            next_questions = self._get_questions_for_multiple_answers(question_id, answer)
        else:
            next_questions = self._get_questions_for_single_answer(question_id, answer)
        
        # Ensure it's a list
        if isinstance(next_questions, str):
            next_questions = [next_questions]
            
        self._add_questions_to_queue(state, next_questions)

    def _get_branch_questions(self, question_id: str, answer: Any) -> List[str]:
        """Get branch questions for a given answer."""
        if isinstance(answer, str):
            branches = self.question_graph[question_id]['branches']
            return branches.get(answer, []) if answer in branches else []
        
        # Handle list answers
        branch_questions = []
        answers_to_check = answer if isinstance(answer, list) else [answer]
        
        for single_answer in answers_to_check:
            if single_answer in self.question_graph[question_id]['branches']:
                branch_result = self.question_graph[question_id]['branches'][single_answer]
                if isinstance(branch_result, str):
                    branch_questions.append(branch_result)
                else:
                    branch_questions.extend(branch_result)
        
        return branch_questions

    def _get_questions_for_multiple_answers(self, question_id: str, answers: List[str]) -> List[str]:
        """Get questions for multiple choice answers."""
        next_questions = []
        for single_answer in answers:
            if (question_id in self.question_graph and 
                single_answer in self.question_graph[question_id]['branches']):
                branch_result = self.question_graph[question_id]['branches'][single_answer]
                if isinstance(branch_result, str):
                    next_questions.append(branch_result)
                else:
                    next_questions.extend(branch_result)
        return next_questions

    def _get_questions_for_single_answer(self, question_id: str, answer: str) -> List[str]:
        """Get questions for single choice answer."""
        if (question_id in self.question_graph and 
            answer in self.question_graph[question_id]['branches']):
            return self.question_graph[question_id]['branches'][answer]
        elif (question_id in self.question_graph and 
              self.question_graph[question_id].get('next_default')):
            return self.question_graph[question_id]['next_default']
        return []

    def _add_questions_to_queue(self, state: Dict[str, Any], questions: List[str]) -> None:
        """Add new questions to the queue if not already answered or queued."""
        queue = state['queue']
        answered = state['answered_questions']
        
        for q_id in questions:
            if self._is_question_available_for_queue(q_id, answered, queue):
                queue.append(q_id)
                self.added_participating_questions_count += 1

    async def save_completed_questionnaire(self, user_id: str) -> bool:
        """
        Save a completed questionnaire to the database.
        
        Args:
            user_id: The user's unique identifier
            
        Returns:
            True if successful, False otherwise
        """
        # Get current state
        state = await self.get_user_state(user_id)
        
        async def save_operation():
            # Prepare answers in a structured format
            structured_answers_list = []
            for q_id, answer_val in state['answers'].items():
                question_text_val = self.basic_information_questions.get(q_id, {}).get('text') or \
                                self.dynamic_questionnaire.get(q_id, {}).get('text', 'Unknown Question')
                structured_answers_list.append({
                    "question_id": q_id,
                    "question_text": question_text_val,
                    "answer": answer_val
                })
            
            # Create completed questionnaire record
            completed_data = CompletedQuestionnaire(
                user_id=user_id,
                answers=json.dumps(structured_answers_list),  # Store as JSON string
                questionnaire_version=state['version'],
                submitted_at=datetime.utcnow(),
                question_count=len(state['answered_questions']),
            )
            
            self.db_session.add(completed_data)
            
            # Clean up temporary state after successful save
            await self._delete_user_state_from_db(user_id)
            delete_cache(get_questionnaire_cache_key(user_id))
        
        return await self._execute_db_operation("saving completed questionnaire", save_operation)
        
    def _get_potential_dynamic_question_ids(self, state: Dict[str, Any]) -> List[str]:
        """
        Get a list of potential dynamic question IDs based on answers to basic questions.
        """
        potential_questions_set = set()
        answered_basic_q_ids = [
            qid for qid in state['answered_questions'] if qid in self.basic_information_questions
        ]

        for bq_id in answered_basic_q_ids:
            if bq_id in self.question_graph:
                question_node_data = self.question_graph[bq_id]
                answer_to_bq_val = state['answers'].get(bq_id)

                # Handle if answer_to_bq_val is a list (e.g., from multiple choice)
                answers_to_check_list = []
                if isinstance(answer_to_bq_val, list):
                    answers_to_check_list.extend(answer_to_bq_val)
                elif answer_to_bq_val is not None: # Ensure it's not None before adding
                    answers_to_check_list.append(answer_to_bq_val)

                for individual_answer_val in answers_to_check_list:
                    if individual_answer_val in question_node_data['branches']:
                        branched_q_ids_list = question_node_data['branches'][individual_answer_val]
                        # Ensure branched_q_ids_list is a list
                        if isinstance(branched_q_ids_list, str):
                            branched_q_ids_list = [branched_q_ids_list]
                        
                        for q_id_val in branched_q_ids_list:
                            if q_id_val in self.dynamic_questionnaire and \
                               q_id_val not in state['answered_questions'] and \
                               q_id_val not in state['queue']: # Avoid adding if already slated
                                potential_questions_set.add(q_id_val)
        
        # If specific branches don't yield enough, could add generic dynamic questions as a fallback
        # For now, only using directly suggested ones.
        # Example Fallback:
        # if not potential_questions_set:
        #     for dq_id in self.dynamic_questionnaire.keys():
        #         if dq_id not in state['answered_questions'] and dq_id not in state['queue']:
        #             potential_questions_set.add(dq_id)

        return list(potential_questions_set)

    def _add_relevant_dynamic_questions(self, state: Dict[str, Any], count: int) -> None:
        """
        Adds a specified number of relevant dynamic questions to the user's queue.
        """
        potential_q_ids = self._get_potential_dynamic_question_ids(state)
        
        # Further filter to ensure questions are not already answered or in the current queue
        # (though _get_potential_dynamic_question_ids already does some of this)
        relevant_q_ids_to_add = [
            q_id for q_id in potential_q_ids 
            if q_id not in state['answered_questions'] and q_id not in state['queue']
        ]
        
        # Sort or prioritize if necessary (e.g., by a predefined order or relevance score)
        # For now, just take the first 'count'
        questions_to_add_to_queue = relevant_q_ids_to_add[:count]
        
        if questions_to_add_to_queue:
            state['queue'].extend(questions_to_add_to_queue)
            logger.debug(f"Added {len(questions_to_add_to_queue)} dynamic questions to queue for user.")
        else:
            logger.debug("No relevant dynamic questions found to add to queue.")

    def _create_default_questions(self) -> None:
        """Create default questions as fallback when loading fails."""
        logger.warning("Creating default questions as fallback")
        self.basic_information_questions = {
            "default_question": {
                "id": "default_question",
                "text": "Default question - please check your question files",
                "type": "text",
                "required": True
            }
        }
        self.dynamic_questionnaire = {}
        self.question_graph = self._build_question_graph()