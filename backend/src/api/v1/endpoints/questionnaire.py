"""API endpoints for the questionnaire system."""
import json
import logging
from typing import Dict, Any, Optional, List, Tuple
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.middleware.auth import verify_firebase_user, get_current_user
from src.models.schemas import QuestionModel
from src.models.database import get_db
from src.services.QuestionnaireService import QuestionnaireService, CONTINUATION_PROMPT_ID
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter()

class QuestionnaireAnswersRequest(BaseModel):
    """Request model for submitting answers."""
    answers: Dict[str, Any]

class NextQuestionResponse(BaseModel):
    """Response model for next question endpoint."""
    question: Optional[QuestionModel] = None
    is_complete: bool = False
    progress: Optional[float] = None  # Percentage of completion
    current_stage_total_questions: Optional[int] = None # New field for UI
    current_stage_answered_questions: Optional[int] = None # New field for UI

async def _calculate_questionnaire_progress(
    user_state: Optional[Dict[str, Any]],
    questionnaire_service: QuestionnaireService
) -> Optional[float]:
    if not user_state:
        return 0.0

    answered_questions = user_state.get('answered_questions', [])
    queue = user_state.get('queue', [])
    current_question_id = queue[0] if queue else None
    answers = user_state.get('answers', {})

    total_basic_q_count = questionnaire_service.get_basic_questions_length()
    num_answered_basic = sum(1 for qid in answered_questions if qid in questionnaire_service.basic_information_questions)

    # Stage 1: Basic Questions
    if num_answered_basic < total_basic_q_count:
        if total_basic_q_count == 0: # Avoid division by zero if no basic questions
            return 0.0 
        return round((num_answered_basic / total_basic_q_count) * 100, 1)

    # Check if continuation prompt was answered "yes"
    continuation_answered_yes = answers.get(CONTINUATION_PROMPT_ID) == "Continue with more questions" or answers.get(CONTINUATION_PROMPT_ID) == "yes"
    
    # Stage 2: Continuation Prompt itself is the current question
    if current_question_id == CONTINUATION_PROMPT_ID:
        # Progress can be considered 100% of basic, or a step beyond basic.
        # Let's show it as if basic is done, and this is an extra step.
        # For frontend to show "X of Y", Y needs to be stable for this stage.
        # We can consider total_basic_q_count + 1 (for the prompt itself) as the "total" for this phase.
        # The number "answered" is num_answered_basic.
        # This will make the progress bar display X of (total_basic_q_count + 1).
        # The percentage should reflect being at this prompt step.
        denominator = total_basic_q_count + 1 # basic questions + continuation prompt
        if denominator == 0: return 100.0 # Should not happen if prompt is active
        return round((num_answered_basic / denominator) * 100, 1)

    # Stage 3: Dynamic Questions (after continuation prompt was answered "yes")
    # This stage is active if the continuation prompt was answered "yes"
    # AND there are dynamic questions in the queue.
    if continuation_answered_yes and queue:
        # Filter out non-dynamic questions from the queue to count only dynamic ones for this stage
        dynamic_questions_in_queue = [qid for qid in queue if qid in questionnaire_service.dynamic_questionnaire]
        
        # Count how many dynamic questions were *added* in the current batch (e.g., 5)
        # This requires knowing how many dynamic questions are expected in this batch.
        # Let's assume for now it's always a batch of 5.
        # A more robust way would be to get this from QuestionnaireService or state.
        current_batch_total = 5 # Number of dynamic questions per batch
        
        # Count how many *dynamic* questions from *this batch* have been answered.
        # This is tricky because `answered_questions` is cumulative.
        # We need to identify dynamic questions answered *after* the last continuation prompt.
        
        # Find the index of the last answered continuation prompt
        last_continuation_prompt_index = -1
        for i in range(len(answered_questions) - 1, -1, -1):
            if answered_questions[i] == CONTINUATION_PROMPT_ID:
                last_continuation_prompt_index = i
                break
        
        # Count dynamic questions answered since the last continuation prompt
        answered_dynamic_in_current_batch = 0
        if last_continuation_prompt_index != -1:
            for i in range(last_continuation_prompt_index + 1, len(answered_questions)):
                if answered_questions[i] in questionnaire_service.dynamic_questionnaire:
                    answered_dynamic_in_current_batch += 1
        
        # If no continuation prompt was answered yet (e.g. first batch of dynamic Qs is not via prompt, though current logic is via prompt)
        # This part might need adjustment based on how initial dynamic Qs are added if not via prompt
        # For now, this path assumes a continuation prompt preceded this dynamic batch.

        # The progress is (answered_dynamic_in_current_batch / current_batch_total)
        # The frontend will need to know current_batch_total is 5 (or whatever it is)
        # And answered_dynamic_in_current_batch is the "current" number for "X of 5"
        if current_batch_total == 0: return 100.0 # Avoid division by zero
        
        # To make the progress bar show X of 5, we calculate percentage of this batch
        # We also need to communicate "current_batch_total" and "answered_dynamic_in_current_batch" to frontend
        # The `progress` field in `NextQuestionResponse` is a single float.
        # We might need to adjust `NextQuestionResponse` or how frontend interprets progress.
        
        # For now, let's return a progress value that implies this sub-stage.
        # A simple way is to add a large offset to basic completion.
        # E.g., 100% (basic) + (answered_in_batch / batch_total * 10-20% of overall questionnaire)
        # This approach is complex for the single float.
        
        # Simpler: Return progress within the current batch of 5.
        # Frontend needs to be aware it's in a "dynamic batch" stage.
        # This could be indicated by a new field in NextQuestionResponse or by convention
        # if currentQuestion.category == "Dynamic" (or similar).
        
        # Let's try to make the frontend logic simpler by having the backend calculate the total number of questions for the current view.
        # If in basic stage, total = total_basic_q_count
        # If in continuation prompt, total = total_basic_q_count + 1
        # If in dynamic stage after "yes", total = 5 (for the current batch)
        # The number of "completed" for the progress bar would be num_answered_basic, num_answered_basic, or answered_dynamic_in_current_batch.
        
        # The `progress` field is a float. We might need to encode stage information differently.
        # For now, focusing on the percentage for the dynamic batch:
        progress_within_batch = (answered_dynamic_in_current_batch / current_batch_total) * 100
        
        # To distinguish this from basic question progress, let's assume basic is 0-80%,
        # continuation prompt is ~80-85%, dynamic questions are 85-100%.
        # This requires careful thought on overall progress representation.
        
        # Let's keep it simple: if in a dynamic batch, progress is for that batch.
        # The frontend will need an update to display "X of 5" instead of "X of total_overall_questions".
        # This means NextQuestionResponse needs to carry more info than just a single progress float.
        
        # For now, the user wants "1 of 5" type display.
        # This implies the `progress` returned to frontend should be based on the batch.
        # And frontend needs to know the "total" for this stage is 5.

        return round(progress_within_batch, 1)


    # Stage 4: Completed (queue is empty)
    if not queue:
        # If continuation was answered "yes" but no dynamic questions were added (or all done)
        if continuation_answered_yes:
            return 100.0 
        # If continuation was answered "no" or skipped, and basic are done.
        if num_answered_basic == total_basic_q_count:
            return 100.0
        # Fallback if somehow here without basic done (should be caught by stage 1)
        return 0.0 if not answered_questions else 100.0


    # Fallback for any other unhandled state (should ideally not be reached if logic is complete)
    logger.warning(f"Unhandled state in progress calculation: {user_state}")
    effective_total_questions = len(answered_questions) + len(queue)
    if effective_total_questions == 0:
        return 0.0
    return round((len(answered_questions) / effective_total_questions) * 100, 1)

@router.get("/start",
            response_model=NextQuestionResponse,
            summary="Start or resume a questionnaire",
            dependencies=[Depends(verify_firebase_user)])
async def start_questionnaire(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Start a new questionnaire or resume an existing one."""
    try:
        user_id = current_user.firebase_uid
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail="User ID not found"
            )
            
        questionnaire_service = QuestionnaireService(db)
        
        next_question, is_complete = await questionnaire_service.get_next_question(user_id)
        
        user_state = await questionnaire_service.get_user_state(user_id)
        progress = await _calculate_questionnaire_progress(user_state, questionnaire_service)
        current_stage_total, current_stage_answered = await _get_current_stage_counts(user_state, questionnaire_service)
        
        return NextQuestionResponse(
            question=next_question,
            is_complete=is_complete,
            progress=progress,
            current_stage_total_questions=current_stage_total,
            current_stage_answered_questions=current_stage_answered
        )
    except Exception as e:
        logger.error(f"Error starting questionnaire: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/next",
            response_model=NextQuestionResponse,
            summary="Get the next question based on current answers",
            dependencies=[Depends(verify_firebase_user)])
async def get_next_question_endpoint(
    request: QuestionnaireAnswersRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get the next question based on provided answers."""
    try:
        user_id = current_user.firebase_uid
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail="User ID not found"
            )
            
        questionnaire_service = QuestionnaireService(db)
        
        next_question, is_complete = await questionnaire_service.get_next_question(
            user_id, 
            request.answers
        )
        
        user_state = await questionnaire_service.get_user_state(user_id)
        progress = await _calculate_questionnaire_progress(user_state, questionnaire_service)
        current_stage_total, current_stage_answered = await _get_current_stage_counts(user_state, questionnaire_service)
        
        return NextQuestionResponse(
            question=next_question,
            is_complete=is_complete,
            progress=progress,
            current_stage_total_questions=current_stage_total,
            current_stage_answered_questions=current_stage_answered
        )
    except Exception as e:
        logger.error(f"Error getting next question: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/submit",
             status_code=status.HTTP_201_CREATED,
             summary="Submit completed questionnaire",
             dependencies=[Depends(verify_firebase_user)])
async def submit_questionnaire(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Submit a completed questionnaire to save the answers permanently."""
    try:
        user_id = current_user.firebase_uid
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail="User ID not found"
            )
            
        questionnaire_service = QuestionnaireService(db)
        
        # Check if questionnaire is complete
        is_complete = await questionnaire_service.is_questionnaire_completed(user_id)
        if not is_complete:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Questionnaire is not complete. Please answer all questions before submitting."
            )
            
        # Save completed questionnaire
        success = await questionnaire_service.save_completed_questionnaire(user_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save questionnaire results"
            )
            
        return {"message": "Questionnaire submitted successfully"}
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error submitting questionnaire: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/status",
            summary="Get current questionnaire status",
            dependencies=[Depends(verify_firebase_user)])
async def get_questionnaire_status(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get the current status of a user's questionnaire."""
    try:
        user_id = current_user.firebase_uid
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail="User ID not found"
            )
            
        questionnaire_service = QuestionnaireService(db)
        
        # Get user state
        user_state = await questionnaire_service.get_user_state(user_id)
        
        # Calculate progress using the new helper
        progress = await _calculate_questionnaire_progress(user_state, questionnaire_service)
        current_stage_total, current_stage_answered = await _get_current_stage_counts(user_state, questionnaire_service)
        
        # Determine completion status based on progress and queue
        # is_complete = await questionnaire_service.is_questionnaire_completed(user_id) # Old way
        is_complete = (progress == 100.0 and not user_state.get('queue')) if progress is not None else False
        
        return {
            "is_complete": is_complete,
            "progress": progress,
            "questions_answered": len(user_state['answered_questions']) if user_state else 0,
            "questions_remaining": len(user_state['queue']) if user_state else 0,
            "current_stage_total_questions": current_stage_total,
            "current_stage_answered_questions": current_stage_answered
        }
    except Exception as e:
        logger.error(f"Error getting questionnaire status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        ) 
    
@router.get("/basic-questions-length",
            summary="Get the number of basic questions",
            response_model=int)
async def get_basic_questions_length(
    db: AsyncSession = Depends(get_db)
):
    """Get the number of basic questions."""
    try:
        questionnaire_service = QuestionnaireService(db)
        count = questionnaire_service.get_basic_questions_length()
        return count
    except Exception as e:
        logger.error(f"Error getting basic questions length: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

async def _get_current_stage_counts(
    user_state: Optional[Dict[str, Any]],
    questionnaire_service: QuestionnaireService
) -> Tuple[Optional[int], Optional[int]]:
    if not user_state:
        return None, None

    answered_questions = user_state.get('answered_questions', [])
    queue = user_state.get('queue', [])
    current_question_id = queue[0] if queue else None
    answers = user_state.get('answers', {})
    
    total_basic_q_count = questionnaire_service.get_basic_questions_length()
    num_answered_basic = sum(1 for qid in answered_questions if qid in questionnaire_service.basic_information_questions)

    # Stage 1: Basic Questions
    if num_answered_basic < total_basic_q_count:
        return total_basic_q_count, num_answered_basic

    continuation_answered_yes = answers.get(CONTINUATION_PROMPT_ID) == "Continue with more questions" or answers.get(CONTINUATION_PROMPT_ID) == "yes"

    # Stage 2: Continuation Prompt
    if current_question_id == CONTINUATION_PROMPT_ID:
        return total_basic_q_count + 1, num_answered_basic # Total includes the prompt itself

    # Stage 3: Dynamic Questions
    if continuation_answered_yes and queue:
        # Count dynamic questions in the current batch (e.g., 5)
        current_batch_total = 0
        dynamic_questions_in_this_batch_in_queue = 0
        
        # Identify dynamic questions currently in the queue for this batch
        # This assumes dynamic questions are added in batches and the queue reflects the current batch
        for qid in queue:
            if qid in questionnaire_service.dynamic_questionnaire:
                dynamic_questions_in_this_batch_in_queue +=1
        
        # Heuristic: Assume batch size is 5 if dynamic questions are present
        # A more robust method would involve service knowing batch size explicitly
        current_batch_total = dynamic_questions_in_this_batch_in_queue 
        if not current_batch_total and any(qid in questionnaire_service.dynamic_questionnaire for qid in queue):
             current_batch_total = 5 # Fallback if queue doesn't only contain this batch's dynamic q's
        elif not any(qid in questionnaire_service.dynamic_questionnaire for qid in queue):
            # This might happen if the queue is empty but we are in "continuation_answered_yes" state
            # which means we are completed.
             pass


        last_continuation_prompt_index = -1
        for i in range(len(answered_questions) - 1, -1, -1):
            if answered_questions[i] == CONTINUATION_PROMPT_ID:
                last_continuation_prompt_index = i
                break
        
        answered_dynamic_in_current_batch = 0
        if last_continuation_prompt_index != -1:
            # Iterate through questions answered *after* the last continuation prompt
            for i in range(last_continuation_prompt_index + 1, len(answered_questions)):
                # Only count dynamic questions that are not the continuation prompt itself
                if answered_questions[i] in questionnaire_service.dynamic_questionnaire and answered_questions[i] != CONTINUATION_PROMPT_ID:
                    answered_dynamic_in_current_batch += 1
        
        # The total for this stage for the UI is the batch size (e.g., 5)
        # We need to ensure current_batch_total is correctly determined.
        # If dynamic_questions_in_this_batch_in_queue is 0 but we know we are in this stage,
        # it means the batch just completed.
        # If queue has dynamic questions, then total = answered_dynamic_in_current_batch + dynamic_questions_in_this_batch_in_queue
        
        # More robust: total number of questions for this dynamic stage is (number of dynamic Qs added for this round)
        # This is typically 5.
        # Let's assume fixed batch size of 5 for now.
        # If dynamic questions were indeed added (check state or a flag)
        
        # Number of dynamic questions expected in a batch
        EXPECTED_DYNAMIC_BATCH_SIZE = 5 
        
        # If we are in the dynamic stage (continuation_answered_yes and not yet complete)
        # The total questions for this stage is EXPECTED_DYNAMIC_BATCH_SIZE
        # The answered questions for this stage is answered_dynamic_in_current_batch
        
        # Check if dynamic questions are actively being processed or just finished
        has_dynamic_in_queue = any(qid in questionnaire_service.dynamic_questionnaire for qid in queue)
        
        if has_dynamic_in_queue or (answered_dynamic_in_current_batch > 0 and answered_dynamic_in_current_batch < EXPECTED_DYNAMIC_BATCH_SIZE) :
             return EXPECTED_DYNAMIC_BATCH_SIZE, answered_dynamic_in_current_batch
        # If no dynamic in queue AND answered_dynamic_in_current_batch is 0 or >= batch_size, means this stage is done or not started within this logic path

    # Stage 4: Completed
    if not queue:
        return len(answered_questions) if answered_questions else 0, len(answered_questions) if answered_questions else 0 # Show all as answered

    # Fallback
    return len(answered_questions) + len(queue), len(answered_questions)