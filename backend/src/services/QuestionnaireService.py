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

logger = logging.getLogger(__name__)

CONTINUATION_PROMPT_ID = "system_continuation_prompt"

# Simplified continuation prompt definition to match standard question structure
CONTINUATION_PROMPT_QUESTION = {
    "id": CONTINUATION_PROMPT_ID,
    "text": "You've completed the initial questions! Would you like to continue with more questions to help us better understand your needs, or submit your responses now?",
    "type": "single-choice",  # Changed to single-choice for standard handling
    "options": ["Continue with more questions", "Submit my responses now"],
    "category": "System",
    "display_type": "continuation_page"  # Special flag for frontend to render this differently
}

class QuestionnaireService:
    """Service for managing questionnaires and user responses."""
    
    def __init__(self, db_session: AsyncSession = None):
        """
        Initialize the questionnaire service.
        
        Args:
            db_session: SQLAlchemy async session for database access
        """
        self.db_session = db_session
        
        # Load question data from files
        try:
            with open('data/sources/basic_information_questions.json', 'r') as f:
                self.basic_information_questions = {q['id']: q for q in json.load(f)}
                
            with open('data/sources/dynamic_questionnaire.json', 'r') as f:
                self.dynamic_questionnaire = {q['id']: q for q in json.load(f)}
                
            # Current questionnaire schema version - increment when structure changes
            self.current_version = 1
            
            # Build the question dependency graph
            self.question_graph = self._build_question_graph()
        except Exception as e:
            logger.error(f"Error loading questionnaire data: {e}")
            # Initialize empty to avoid NoneType errors
            self.basic_information_questions = {}
            self.dynamic_questionnaire = {}
            self.question_graph = {}
            self.current_version = 1

    def _build_question_graph(self) -> Dict[str, Dict[str, Any]]:
        """
        Builds a graph of questions and their dependencies.
        
        Returns:
            A dictionary mapping question IDs to their next questions and branches
        """
        graph = {}
        start_questions = list(self.basic_information_questions.values())

        # Process basic information questions first
        for index, question in enumerate(start_questions):
            # For each question, set up next_default to be the next question in sequence
            graph[question['id']] = {
                "next_default": start_questions[index + 1]['id'] if index < len(start_questions) - 1 else None,
                "branches": {}
            }

            # Add branches if the question has them
            if question.get('branches'):
                for answer, next_questions_val in question['branches'].items():
                    graph[question['id']]['branches'][answer] = next_questions_val

        # Process dynamic questionnaire questions
        for q_id, question in self.dynamic_questionnaire.items():
            graph[q_id] = {
                "next_default": [],
                "branches": {}
            }

            # Add branches for dynamic questions
            if question.get('branches'):
                for answer, next_questions_val in question['branches'].items():
                    graph[q_id]['branches'][answer] = next_questions_val
        
        return graph
        
    async def _get_user_state_from_db(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the user's questionnaire state from the database.
        
        Args:
            user_id: The user's unique identifier
            
        Returns:
            User state as a dictionary or None if not found
        """
        if not self.db_session:
            logger.error("Database session not available")
            return None
            
        try:
            # Query for user state
            query = select(QuestionnaireState).where(QuestionnaireState.user_id == user_id)
            result = await self.db_session.execute(query)
            state_record = result.scalars().first()
            
            if not state_record:
                return None
                
            # Parse JSON fields
            state = {
                'answers': json.loads(state_record.answers),
                'answered_questions': json.loads(state_record.answered_questions),
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
        if not self.db_session:
            logger.error("Database session not available")
            return False
            
        try:
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
                state_record.questionnaire_version = self.current_version
                state_record.last_updated = datetime.utcnow()
            else:
                # Create new record
                state_record = QuestionnaireState(
                    user_id=user_id,
                    queue=json.dumps(queue_list),
                    answers=json.dumps(state['answers']),
                    answered_questions=json.dumps(state['answered_questions']),
                    questionnaire_version=self.current_version,
                    created_at=datetime.utcnow(),
                    last_updated=datetime.utcnow()
                )
                self.db_session.add(state_record)
                
            await self.db_session.commit()
            return True
        except Exception as e:
            logger.error(f"Error updating user state in DB: {e}")
            await self.db_session.rollback()
            return False
            
    async def _delete_user_state_from_db(self, user_id: str) -> bool:
        """
        Delete the user's questionnaire state from the database.
        
        Args:
            user_id: The user's unique identifier
            
        Returns:
            True if successful, False otherwise
        """
        if not self.db_session:
            logger.error("Database session not available")
            return False
            
        try:
            # Delete state record
            query = delete(QuestionnaireState).where(QuestionnaireState.user_id == user_id)
            await self.db_session.execute(query)
            await self.db_session.commit()
            return True
        except Exception as e:
            logger.error(f"Error deleting user state from DB: {e}")
            await self.db_session.rollback()
            return False
            
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
        queue = deque(list(self.basic_information_questions.keys()))
        
        return {
            'queue': queue,
            'answers': {},
            'answered_questions': [],
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
                if q_id not in state['answered_questions']:
                    state['answers'][q_id] = answer_val
                    state['answered_questions'].append(q_id)
                    
                    # Update queue based on the answer
                    self._update_queue_based_on_answer(state, q_id, answer_val)
        
        # Save updated state
        await self.update_user_state(user_id, state)
        
        # Check if we should show the continuation prompt
        # Show after first 6 questions, then after every 5 additional questions
        answered_count = len(state['answered_questions'])
        continuation_prompt_shown_or_answered = CONTINUATION_PROMPT_ID in state['answered_questions'] or \
                                              CONTINUATION_PROMPT_ID in list(state['queue'])
        
        # Count the number of times the continuation prompt has been shown
        continuation_prompt_times = len([q_id for q_id in state['answered_questions'] if q_id == CONTINUATION_PROMPT_ID])
        
        # Calculate the threshold for when to show the next continuation prompt
        # First at 6 questions, then at 6+5=11, 11+5=16, etc.
        next_prompt_threshold = 6 + (continuation_prompt_times * 5)
        
        # If threshold reached and continuation prompt isn't already in play
        if answered_count >= next_prompt_threshold and not continuation_prompt_shown_or_answered:
            logger.debug(f"{answered_count} questions answered for user {user_id}. Adding continuation prompt.")
            state['queue'].appendleft(CONTINUATION_PROMPT_ID)  # Use appendleft to add to front of queue
            await self.update_user_state(user_id, state)  # Save state with prompt in queue

        # Return the next question if available
        if state['queue']:
            next_q_id = state['queue'][0]
            next_question_data = None
            
            if next_q_id == CONTINUATION_PROMPT_ID:
                next_question_data = CONTINUATION_PROMPT_QUESTION
            elif next_q_id in self.basic_information_questions:
                next_question_data = self.basic_information_questions[next_q_id]
            elif next_q_id in self.dynamic_questionnaire:
                next_question_data = self.dynamic_questionnaire[next_q_id]
                
            return next_question_data, False
        
        # No more questions, questionnaire is complete
        return None, True
    
    def get_basic_questions_length(self) -> int:
        """
        Get the number of basic questions.
        """
        return len(self.basic_information_questions)
        
    def _update_queue_based_on_answer(self, state: Dict[str, Any], question_id: str, answer: Any) -> None:
        """
        Update the question queue based on a user's answer.
        
        Args:
            state: Current user state
            question_id: The ID of the answered question
            answer: The user's answer (could be a string, list, or JSON-encoded string)
        """
        queue = state['queue']
        answered = state['answered_questions']
        
        # Parse JSON string if needed (handles cases like '["option1","option2"]')
        if isinstance(answer, str) and answer.startswith('[') and answer.endswith(']'):
            try:
                answer = json.loads(answer)
                # Update the answer in the state to use the parsed version
                state['answers'][question_id] = answer
                logger.debug(f"Parsed JSON answer for question {question_id}: {answer}")
            except json.JSONDecodeError:
                # If it's not valid JSON, keep it as a string
                logger.debug(f"Received a string that looks like JSON but isn't: {answer}")
        
        # Handle the continuation prompt specifically
        if question_id == CONTINUATION_PROMPT_ID:
            logger.debug(f"Processing continuation prompt answer. Answer type: {type(answer)}, value: {answer}")
            
            # Extract actual answer regardless of format (simplify processing)
            actual_answer_val = None
            
            # Check if it's a string that contains our expected responses
            if isinstance(answer, str):
                if "continue" in answer.lower() or answer.lower() == "yes" or answer == "Continue with more questions":
                    actual_answer_val = "yes"
                else:
                    actual_answer_val = "no"
            # Handle if answer is a list or any other type - default to "no"
            else:
                logger.warning(f"Unexpected answer type for continuation prompt: {type(answer)}")
                actual_answer_val = "no"
                
            logger.debug(f"Processed continuation answer: {actual_answer_val}")
            
            # If user wants to continue, add more questions
            if actual_answer_val == "yes":
                self._add_relevant_dynamic_questions(state, count=5)
                
            # Always remove the continuation prompt from the queue 
            if queue and queue[0] == CONTINUATION_PROMPT_ID:
                queue.popleft()
            elif CONTINUATION_PROMPT_ID in queue:
                # For deque, we need to remove the item safely
                queue_list_val = list(queue)
                if CONTINUATION_PROMPT_ID in queue_list_val:
                    queue_list_val.remove(CONTINUATION_PROMPT_ID)
                    state['queue'] = deque(queue_list_val)
                    
            return  # Exit early as we've handled this special case

        # Remove the answered question from queue if it's at the front
        if queue and queue[0] == question_id:
            queue.popleft()  # Using popleft() for deque instead of pop(0)
        elif question_id in queue:
            # For deque, we need to convert to list, remove the element, and convert back
            queue_list_val = list(queue)
            queue_list_val.remove(question_id)
            state['queue'] = deque(queue_list_val)
        
        # Process basic information questions
        if question_id in self.basic_information_questions:
            # Add branch questions if applicable
            if question_id in self.question_graph:
                if isinstance(answer, str):
                    # Only look up branches if the answer is in the branches dictionary
                    if answer in self.question_graph[question_id]['branches']:
                        branch_questions_list = self.question_graph[question_id]['branches'][answer]
                    else:
                        branch_questions_list = []
                else:
                    # Handle case where answer is a list of strings
                    branch_questions_list = []
                    for single_answer_val in answer if isinstance(answer, list) else [answer]:
                        if single_answer_val in self.question_graph[question_id]['branches']:
                            branch_q_for_answer_val = self.question_graph[question_id]['branches'][single_answer_val]
                            # Make sure we're always extending with a list
                            if isinstance(branch_q_for_answer_val, str):
                                branch_questions_list.append(branch_q_for_answer_val)
                            else:
                                branch_questions_list.extend(branch_q_for_answer_val)
                
                # Ensure branch_questions_list is a list
                if isinstance(branch_questions_list, str):
                    branch_questions_list = [branch_questions_list]
                    
                # Add each branch question that hasn't been answered yet
                for q_id_val in branch_questions_list:
                    if q_id_val not in answered and q_id_val not in queue:
                        queue.append(q_id_val)
        
        # Process dynamic questions similarly to basic questions
        elif question_id in self.dynamic_questionnaire:
            next_questions_list = []
            
            # Handle multiple-choice answers (list or JSON-parsed list)
            if isinstance(answer, list):
                for single_answer_val in answer:
                    if (question_id in self.question_graph and 
                        single_answer_val in self.question_graph[question_id]['branches']):
                        branch_q_val = self.question_graph[question_id]['branches'][single_answer_val]
                        if isinstance(branch_q_val, str):
                            next_questions_list.append(branch_q_val)
                        else:
                            next_questions_list.extend(branch_q_val)
            # Handle single choice
            elif (question_id in self.question_graph and 
                  answer in self.question_graph[question_id]['branches']):
                next_questions_list = self.question_graph[question_id]['branches'][answer]
            # Handle default case
            elif (question_id in self.question_graph and 
                  self.question_graph[question_id].get('next_default')):
                next_questions_list = self.question_graph[question_id]['next_default']
            
            # Ensure next_questions_list is a list
            if isinstance(next_questions_list, str):
                next_questions_list = [next_questions_list]
                
            # Add new questions to queue
            for q_id_val in next_questions_list:
                if q_id_val and q_id_val not in answered and q_id_val not in queue:
                    queue.append(q_id_val)
    
    async def save_completed_questionnaire(self, user_id: str) -> bool:
        """
        Save a completed questionnaire to the database.
        
        Args:
            user_id: The user's unique identifier
            
        Returns:
            True if successful, False otherwise
        """
        if not self.db_session:
            logger.error("Database session not available")
            return False
            
        # Get current state
        state = await self.get_user_state(user_id)
        
        # Verify questionnaire is complete
        if state['queue'] and len(state['queue']) > 0:
            logger.error(f"Cannot save incomplete questionnaire for user {user_id}")
            return False
            
        try:
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
            await self.db_session.commit()
            
            # Clean up temporary state
            await self._delete_user_state_from_db(user_id)
            delete_cache(get_questionnaire_cache_key(user_id))
            
            return True
        except Exception as e:
            logger.error(f"Error saving completed questionnaire: {e}")
            await self.db_session.rollback()
            return False
            
    async def is_questionnaire_completed(self, user_id: str) -> bool:
        """
        Check if a user's questionnaire is completed.
        
        Args:
            user_id: The user's unique identifier
            
        Returns:
            True if completed, False otherwise
        """
        state = await self.get_user_state(user_id)
        
        # If the queue is not empty, it's not complete, 
        # unless the only thing in the queue is the continuation prompt AND no decision has been made.
        # However, if continuation prompt is answered "no" and queue becomes empty, it IS complete.
        # If continuation prompt is answered "yes" and new questions are added, it is NOT complete until those are done.
        
        # Simplest check: if queue is empty AND there are answered questions, it implies completion.
        # The logic in get_next_question and _update_queue_based_on_answer handles the flow
        # such that an empty queue signifies true completion or a point where user opted out.
        return (not state['queue']) and state['answered_questions']
        
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
        
        
        