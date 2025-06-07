"""API endpoints for the questionnaire system."""
import json
import logging
from typing import Dict, Any, Optional, List, Tuple
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi.responses import JSONResponse

from src.middleware.auth import verify_firebase_user, get_current_user
from src.models.schemas import QuestionModel
from src.models.database import get_db
from src.services.QuestionnaireService import QuestionnaireService
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
    show_continuation_prompt: bool = False # Indicate when to show continuation prompt

async def _calculate_questionnaire_progress(
    user_state: Optional[Dict[str, Any]],
    questionnaire_service: QuestionnaireService
) -> Optional[float]:
    if not user_state:
        return 0.0

    answered_questions = user_state.get('answered_questions', [])
    num_answered = len(answered_questions)
    
    if num_answered <= 10:
        # First batch: 10 questions
        target_batch_size = 10
    else:
        # Calculate which batch we're in after the first batch
        additional_batches = (num_answered - 10 + 4) // 5  
        target_batch_size = 10 + (additional_batches * 5)
    
    # Get total available questions count (answered + in queue + potential future questions)
    total_questions = len(questionnaire_service.basic_information_questions) + len(questionnaire_service.dynamic_questionnaire)
    
    # Limit the target batch size to the total number of available questions
    target_batch_size = min(target_batch_size, total_questions)
    
    if num_answered >= total_questions:
        return 100.0
    
    if target_batch_size > 0:
        progress = (num_answered / target_batch_size) * 100
        return round(min(progress, 100.0), 1)
    
    return 100.0

def should_show_continuation_prompt(
    user_state: Optional[Dict[str, Any]]
) -> bool:
    """
    Determine if a continuation prompt should be shown based on question counts.
    """
    if not user_state:
        return False
        
    answered_questions = user_state.get('answered_questions', [])
    num_answered = len(answered_questions)

    if num_answered == 10 or (num_answered > 10 and (num_answered - 10) % 5 == 0):
        return True
    
    return False

def should_show_final_prompt(
    user_state: Optional[Dict[str, Any]],
    questionnaire_service: QuestionnaireService
) -> bool:
    """
    Determine if the final completion prompt should be shown.
    This is different from just is_complete - it specifically checks
    if we should show the special completion page.
    """
    if not user_state:
        return False
    
    # Check if there are any questions left
    answered_questions = user_state.get('answered_questions', [])
    queue = user_state.get('queue', [])
    
    # All basic info questions and dynamic questions
    all_question_ids = list(questionnaire_service.basic_information_questions.keys()) + list(questionnaire_service.dynamic_questionnaire.keys())
    
    # Check if all questions have been answered
    all_answered = all(q_id in answered_questions for q_id in all_question_ids)
    
    # Queue is empty and all questions answered
    return not queue and all_answered

# Create constants for completion prompt
COMPLETION_PROMPT = {
    "id": "final_completion_prompt",
    "text": "Congratulations! You've completed all the questions. Your preferences have been saved and we're ready to find the perfect apartments for you.",
    "type": "single-choice",
    "options": ["View matched apartments", "Go to dashboard"],
    "category": "System",
    "display_type": "continuation_page"  # Reuse the same display type
}

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
        
        user_state = await questionnaire_service.get_user_state(user_id)
        
        # Check if we should show the completion prompt
        show_final = should_show_final_prompt(user_state, questionnaire_service)
        if show_final:
            progress = await _calculate_questionnaire_progress(user_state, questionnaire_service)
            current_stage_total, current_stage_answered = await _get_current_stage_counts(user_state, questionnaire_service)
            
            logger.info(f"Showing final completion prompt for user {user_id}")
            
            return NextQuestionResponse(
                question=COMPLETION_PROMPT,
                is_complete=True,
                progress=100.0,
                current_stage_total_questions=current_stage_total,
                current_stage_answered_questions=current_stage_answered,
                show_continuation_prompt=False
            )
        
        # Check if we should show the continuation prompt
        show_prompt = should_show_continuation_prompt(user_state)
        
        # If we need to show a continuation prompt, return a special response
        if show_prompt and not show_final:
            progress = await _calculate_questionnaire_progress(user_state, questionnaire_service)
            current_stage_total, current_stage_answered = await _get_current_stage_counts(user_state, questionnaire_service)
            
            logger.info(f"Showing continuation prompt for user {user_id}")
            
            # Return response with continuation prompt flag
            return NextQuestionResponse(
                question=None,  # No question, just the prompt
                is_complete=False,
                progress=progress,
                current_stage_total_questions=current_stage_total,
                current_stage_answered_questions=current_stage_answered,
                show_continuation_prompt=True
            )
        
        # Normal flow - get the next question
        next_question, is_complete, _ = await questionnaire_service.get_next_question(user_id)
        
        # If complete but no more questions, show completion prompt
        if is_complete:
            return NextQuestionResponse(
                question=COMPLETION_PROMPT,
                is_complete=True,
                progress=100.0,
                current_stage_total_questions=0,
                current_stage_answered_questions=0,
                show_continuation_prompt=False
            )
        
        progress = await _calculate_questionnaire_progress(user_state, questionnaire_service)
        current_stage_total, current_stage_answered = await _get_current_stage_counts(user_state, questionnaire_service)
        
        return NextQuestionResponse(
            question=next_question,
            is_complete=is_complete,
            progress=progress,
            current_stage_total_questions=current_stage_total,
            current_stage_answered_questions=current_stage_answered,
            show_continuation_prompt=False
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
        
        is_user_chose_to_continue = False
        # Process answers if provided
        if request.answers:
            next_question, is_complete, is_user_chose_to_continue = await questionnaire_service.get_next_question(
                user_id, 
                request.answers
            )
        
        # Get updated state after applying answers
        user_state = await questionnaire_service.get_user_state(user_id)
        
        # Check if we should show the completion prompt
        show_final = should_show_final_prompt(user_state, questionnaire_service)
        if show_final:
            progress = await _calculate_questionnaire_progress(user_state, questionnaire_service)
            current_stage_total, current_stage_answered = await _get_current_stage_counts(user_state, questionnaire_service)
            
            logger.info(f"Showing final completion prompt for user {user_id}")
            
            return NextQuestionResponse(
                question=COMPLETION_PROMPT,
                is_complete=True,
                progress=100.0,
                current_stage_total_questions=current_stage_total,
                current_stage_answered_questions=current_stage_answered,
                show_continuation_prompt=False
            )
        
        show_prompt = should_show_continuation_prompt(user_state)
        
        # If we need to show a continuation prompt, return a special response
        if show_prompt and not is_user_chose_to_continue:
            progress = await _calculate_questionnaire_progress(user_state, questionnaire_service)
            current_stage_total, current_stage_answered = await _get_current_stage_counts(user_state, questionnaire_service)
            
            logger.info(f"Showing continuation prompt for user {user_id}")
            
            # Return response with continuation prompt flag
            return NextQuestionResponse(
                question=None,  # No question, just the prompt
                is_complete=False,
                progress=progress,
                current_stage_total_questions=current_stage_total,
                current_stage_answered_questions=current_stage_answered,
                show_continuation_prompt=True
            )
        
        # If we already have next_question from processing answers, use it
        if 'next_question' in locals() and next_question:
            progress = await _calculate_questionnaire_progress(user_state, questionnaire_service)
            current_stage_total, current_stage_answered = await _get_current_stage_counts(user_state, questionnaire_service)
            
            if is_complete:
                return NextQuestionResponse(
                    question=COMPLETION_PROMPT,
                    is_complete=True,
                    progress=100.0,
                    current_stage_total_questions=0,
                    current_stage_answered_questions=0,
                    show_continuation_prompt=False
                )
            
            return NextQuestionResponse(
                question=next_question,
                is_complete=is_complete,
                progress=progress,
                current_stage_total_questions=current_stage_total,
                current_stage_answered_questions=current_stage_answered,
                show_continuation_prompt=False
            )
        
        # Normal flow - get the next question
        next_question, is_complete, _ = await questionnaire_service.get_next_question(user_id)
        
        if is_complete:
            return NextQuestionResponse(
                question=COMPLETION_PROMPT,
                is_complete=True,
                progress=100.0,
                current_stage_total_questions=0,
                current_stage_answered_questions=0,
                show_continuation_prompt=False
            )
        
        progress = await _calculate_questionnaire_progress(user_state, questionnaire_service)
        current_stage_total, current_stage_answered = await _get_current_stage_counts(user_state, questionnaire_service)
        
        return NextQuestionResponse(
            question=next_question,
            is_complete=is_complete,
            progress=progress,
            current_stage_total_questions=current_stage_total,
            current_stage_answered_questions=current_stage_answered,
            show_continuation_prompt=False
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
        
        # First check if a completed questionnaire exists
        from src.models.models import CompletedQuestionnaire
        has_completed = await db.execute(
            select(CompletedQuestionnaire).where(CompletedQuestionnaire.user_id == user_id)
        )
        completed_questionnaire = has_completed.scalars().first()
        
        if completed_questionnaire:
            # User has a submitted questionnaire in the database
            logger.info(f"User {user_id} has a completed questionnaire in the database")
            return {
                "is_complete": True,
                "questions_answered": completed_questionnaire.question_count,
            }
        
        # Get user state
        user_state = await questionnaire_service.get_user_state(user_id)
        
        # Calculate progress using the new helper
        progress = await _calculate_questionnaire_progress(user_state, questionnaire_service)
        current_stage_total, current_stage_answered = await _get_current_stage_counts(user_state, questionnaire_service)
        
        # Determine completion status based on progress and queue
        # is_complete = await questionnaire_service.is_questionnaire_completed(user_id) # Old way
        is_complete = (progress == 100.0 and not user_state.get('queue')) if progress is not None else False
        
        # Check if we should show the continuation prompt
        show_prompt = should_show_continuation_prompt(user_state)
        
        return {
            "is_complete": is_complete,
            "progress": progress,
            "questions_answered": len(user_state['answered_questions']) if user_state else 0,
            "questions_remaining": len(user_state['queue']) if user_state else 0,
            "current_stage_total_questions": current_stage_total,
            "current_stage_answered_questions": current_stage_answered,
            "show_continuation_prompt": show_prompt
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
    """
    Get the counts for the current question stage.
    Returns (total_questions_in_stage, answered_questions_in_stage)
    """
    if not user_state:
        return None, None

    answered_questions = user_state.get('answered_questions', [])
    num_answered = len(answered_questions)
    
    # Get total available questions count
    participating_questions_count = user_state.get('participating_questions_count', 0)
    is_first_batch = num_answered < 10

    if is_first_batch:
        return 10, num_answered
    else:

        current_batch_number = ((num_answered - 10) // 5) + 1
        batch_start = 10 + ((current_batch_number - 1) * 5)
        batch_end = min(batch_start + 5, participating_questions_count)
        questions_in_current_batch = min(num_answered - batch_start, 5)
        current_batch_size = batch_end - batch_start
        
        return current_batch_size, questions_in_current_batch