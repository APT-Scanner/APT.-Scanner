"""API endpoints for the questionnaire system."""
import json
import logging
from typing import Dict, Any, Optional, List, Tuple
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.middleware.auth import get_current_user
from src.models.schemas import QuestionModel
from src.models.database import get_db
from src.services.QuestionnaireService import QuestionnaireService
from src.models.mongo_db import get_mongo_db
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


async def get_questionnaire_service(db: AsyncSession = Depends(get_db)) -> QuestionnaireService:
    """
    Dependency to create and initialize the QuestionnaireService.
    This ensures that questions are loaded from MongoDB before use.
    """
    if get_mongo_db() is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Questionnaire database is not available."
        )
    service = QuestionnaireService(db)
    await service.load_questions()  # Asynchronously load questions
    return service

async def _calculate_questionnaire_progress(
    user_state: Optional[Dict[str, Any]],
    questionnaire_service: QuestionnaireService
) -> Optional[float]:
    if not user_state:
        return 0.0

    answered_questions = user_state.get('answered_questions', [])
    num_answered = len(answered_questions)
    
    if num_answered <= 10:
        target_batch_size = 10
    else:
        additional_batches = (num_answered - 10 + 4) // 5  
        target_batch_size = 10 + (additional_batches * 5)
    
    total_questions = len(questionnaire_service.basic_information_questions) + len(questionnaire_service.dynamic_questionnaire)
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
    if not user_state:
        return False
    
    answered_questions = user_state.get('answered_questions', [])
    queue = user_state.get('queue', [])
    
    all_question_ids = list(questionnaire_service.basic_information_questions.keys()) + list(questionnaire_service.dynamic_questionnaire.keys())
    
    all_answered = all(q_id in answered_questions for q_id in all_question_ids)
    
    return not queue and all_answered

COMPLETION_PROMPT = {
    "id": "final_completion_prompt",
    "text": "Congratulations! You've completed all the questions. Your preferences have been saved and we're ready to find the perfect apartments for you.",
    "type": "single-choice",
    "options": ["View matched apartments", "Go to dashboard"],
    "category": "System",
    "display_type": "continuation_page"
}

@router.get("/start",
            response_model=NextQuestionResponse,
            summary="Start or resume a questionnaire")
async def start_questionnaire(
    current_user: dict = Depends(get_current_user),
    questionnaire_service: QuestionnaireService = Depends(get_questionnaire_service)
):
    """Start a new questionnaire or resume an existing one."""
    try:
        user_id = current_user.firebase_uid
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail="User ID not found"
            )
            
        user_state = await questionnaire_service.get_user_state(user_id)
        
        show_final = should_show_final_prompt(user_state, questionnaire_service)
        if show_final:
            progress = await _calculate_questionnaire_progress(user_state, questionnaire_service)
            current_stage_total, current_stage_answered = await _get_current_stage_counts(user_state, questionnaire_service)
            return NextQuestionResponse(
                question=COMPLETION_PROMPT, is_complete=True, progress=100.0,
                current_stage_total_questions=current_stage_total,
                current_stage_answered_questions=current_stage_answered,
                show_continuation_prompt=False
            )
        
        show_prompt = should_show_continuation_prompt(user_state)
        if show_prompt and not show_final:
            progress = await _calculate_questionnaire_progress(user_state, questionnaire_service)
            current_stage_total, current_stage_answered = await _get_current_stage_counts(user_state, questionnaire_service)
            return NextQuestionResponse(
                question=None, is_complete=False, progress=progress,
                current_stage_total_questions=current_stage_total,
                current_stage_answered_questions=current_stage_answered,
                show_continuation_prompt=True
            )
        
        next_question, is_complete, _ = await questionnaire_service.get_next_question(user_id)
        
        if is_complete:
            return NextQuestionResponse(
                question=COMPLETION_PROMPT, is_complete=True, progress=100.0,
                current_stage_total_questions=0, current_stage_answered_questions=0,
                show_continuation_prompt=False
            )
        
        progress = await _calculate_questionnaire_progress(user_state, questionnaire_service)
        current_stage_total, current_stage_answered = await _get_current_stage_counts(user_state, questionnaire_service)
        
        return NextQuestionResponse(
            question=next_question, is_complete=is_complete, progress=progress,
            current_stage_total_questions=current_stage_total,
            current_stage_answered_questions=current_stage_answered,
            show_continuation_prompt=False
        )
    except Exception as e:
        logger.error(f"Error starting questionnaire: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.post("/next",
            response_model=NextQuestionResponse,
            summary="Get the next question based on current answers")
async def get_next_question_endpoint(
    request: QuestionnaireAnswersRequest,
    current_user: dict = Depends(get_current_user),
    questionnaire_service: QuestionnaireService = Depends(get_questionnaire_service)
):
    """Get the next question based on provided answers."""
    try:
        user_id = current_user.firebase_uid
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User ID not found")
        
        next_question, is_complete, is_user_chose_to_continue = await questionnaire_service.get_next_question(
            user_id, request.answers
        )
        
        user_state = await questionnaire_service.get_user_state(user_id)
        
        show_final = should_show_final_prompt(user_state, questionnaire_service)
        if show_final:
            progress = await _calculate_questionnaire_progress(user_state, questionnaire_service)
            current_stage_total, current_stage_answered = await _get_current_stage_counts(user_state, questionnaire_service)
            return NextQuestionResponse(
                question=COMPLETION_PROMPT, is_complete=True, progress=100.0,
                current_stage_total_questions=current_stage_total,
                current_stage_answered_questions=current_stage_answered,
                show_continuation_prompt=False
            )
        
        show_prompt = should_show_continuation_prompt(user_state)
        if show_prompt and not is_user_chose_to_continue:
            progress = await _calculate_questionnaire_progress(user_state, questionnaire_service)
            current_stage_total, current_stage_answered = await _get_current_stage_counts(user_state, questionnaire_service)
            return NextQuestionResponse(
                question=None, is_complete=False, progress=progress,
                current_stage_total_questions=current_stage_total,
                current_stage_answered_questions=current_stage_answered,
                show_continuation_prompt=True
            )

        progress = await _calculate_questionnaire_progress(user_state, questionnaire_service)
        current_stage_total, current_stage_answered = await _get_current_stage_counts(user_state, questionnaire_service)
        
        if is_complete:
            return NextQuestionResponse(
                question=COMPLETION_PROMPT, is_complete=True, progress=100.0,
                current_stage_total_questions=current_stage_total,
                current_stage_answered_questions=current_stage_answered,
                show_continuation_prompt=False
            )

        return NextQuestionResponse(
            question=next_question, is_complete=is_complete, progress=progress,
            current_stage_total_questions=current_stage_total,
            current_stage_answered_questions=current_stage_answered,
            show_continuation_prompt=False
        )
    except Exception as e:
        logger.error(f"Error getting next question: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.post("/submit",
             status_code=status.HTTP_201_CREATED,
             summary="Submit completed questionnaire")
async def submit_questionnaire(
    current_user: dict = Depends(get_current_user),
    questionnaire_service: QuestionnaireService = Depends(get_questionnaire_service)
):
    """Submit a completed questionnaire to save the answers permanently."""
    try:
        user_id = current_user.firebase_uid
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User ID not found")
            
        success = await questionnaire_service.save_completed_questionnaire(user_id)
        if not success:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to save questionnaire results")
            
        return {"message": "Questionnaire submitted successfully"}
    except Exception as e:
        logger.error(f"Error submitting questionnaire: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.get("/status",
            summary="Get current questionnaire status")
async def get_questionnaire_status(
    current_user: dict = Depends(get_current_user),
    questionnaire_service: QuestionnaireService = Depends(get_questionnaire_service)
):
    """Get the current status of a user's questionnaire."""
    try:
        user_id = current_user.firebase_uid
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User ID not found")
            
        completed_questionnaire = await questionnaire_service.get_completed_questionnaire(user_id)
        
        if completed_questionnaire:
            logger.info(f"User {user_id} has a completed questionnaire in MongoDB")
            return {
                "is_complete": True,
                "questions_answered": completed_questionnaire.get("question_count", 0),
            }
        
        user_state = await questionnaire_service.get_user_state(user_id)
        progress = await _calculate_questionnaire_progress(user_state, questionnaire_service)
        current_stage_total, current_stage_answered = await _get_current_stage_counts(user_state, questionnaire_service)
        
        is_complete = (progress == 100.0 and not user_state.get('queue')) if progress is not None else False
        show_prompt = should_show_continuation_prompt(user_state)
        
        return {
            "is_complete": is_complete, "progress": progress,
            "questions_answered": len(user_state.get('answered_questions', [])),
            "questions_remaining": len(user_state.get('queue', [])),
            "current_stage_total_questions": current_stage_total,
            "current_stage_answered_questions": current_stage_answered,
            "show_continuation_prompt": show_prompt
        }
    except Exception as e:
        logger.error(f"Error getting questionnaire status: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.get("/basic-questions-length",
            summary="Get the number of basic questions",
            response_model=int)
async def get_basic_questions_length(
    questionnaire_service: QuestionnaireService = Depends(get_questionnaire_service)
):
    """Get the number of basic questions."""
    try:
        return questionnaire_service.get_basic_questions_length()
    except Exception as e:
        logger.error(f"Error getting basic questions length: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

async def _get_current_stage_counts(
    user_state: Optional[Dict[str, Any]],
    questionnaire_service: QuestionnaireService
) -> Tuple[Optional[int], Optional[int]]:
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