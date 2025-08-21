"""API endpoints for the questionnaire system."""
import logging
from typing import Dict, Any, Optional, Tuple
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.middleware.auth import get_current_user
from src.database.models import User as UserModel
from src.database.schemas import QuestionModel
from src.database.postgresql_db import get_db
from src.services.questionnaire_service import QuestionnaireService
from src.database.mongo_db import get_mongo_db
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
    current_stage_total_questions: Optional[int] = None 
    current_stage_answered_questions: Optional[int] = None
    show_continuation_prompt: bool = False


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
    await service.load_questions()
    return service


@router.get("/current",
            response_model=NextQuestionResponse,
            summary="Get current questionnaire question")
async def get_current_question(
    current_user: UserModel = Depends(get_current_user),
    questionnaire_service: QuestionnaireService = Depends(get_questionnaire_service)
):
    """Get the current questionnaire question or start a new questionnaire."""
    try:
        user_id = current_user.firebase_uid
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail="User ID not found"
            )
            
        result = await questionnaire_service.start_questionnaire(user_id)
        return NextQuestionResponse(**result)
        
    except Exception as e:
        logger.error(f"Error starting questionnaire: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.post("/answers",
            response_model=NextQuestionResponse,
            summary="Submit answers and get next question")
async def submit_answers(
    request: QuestionnaireAnswersRequest,
    current_user: UserModel = Depends(get_current_user),
    questionnaire_service: QuestionnaireService = Depends(get_questionnaire_service)
):
    """Submit answers to current question and get the next question."""
    try:
        user_id = current_user.firebase_uid
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User ID not found")
        
        result = await questionnaire_service.submit_answers(user_id, request.answers)
        return NextQuestionResponse(**result)
        
    except Exception as e:
        logger.error(f"Error getting next question: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.put("/",
             status_code=status.HTTP_200_OK,
             summary="Complete and save questionnaire")
async def complete_questionnaire(
    current_user: UserModel = Depends(get_current_user),
    questionnaire_service: QuestionnaireService = Depends(get_questionnaire_service)
):
    """Complete and save the questionnaire permanently."""
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

@router.post("/current/skip",
            response_model=NextQuestionResponse,
            summary="Skip current question and get next question")
async def skip_current_question(
    current_user: UserModel = Depends(get_current_user),
    questionnaire_service: QuestionnaireService = Depends(get_questionnaire_service)
):
    """Skip the current question by submitting null answer and proceed to the next one."""
    try:
        user_id = current_user.firebase_uid
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User ID not found")
        
        result = await questionnaire_service.skip_question(user_id)
        return NextQuestionResponse(**result)
        
    except Exception as e:
        logger.error(f"Error skipping question: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.get("/status",
            summary="Get current questionnaire status")
async def get_questionnaire_status(
    current_user: UserModel = Depends(get_current_user),
    questionnaire_service: QuestionnaireService = Depends(get_questionnaire_service)
):
    """Get the current status of a user's questionnaire."""
    try:
        user_id = current_user.firebase_uid
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User ID not found")
            
        result = await questionnaire_service.get_questionnaire_status(user_id)
        return result
        
    except Exception as e:
        logger.error(f"Error getting questionnaire status: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.get("/basic-questions-count",
            summary="Get the number of basic questions",
            response_model=int)
async def basic_questions_count(
    questionnaire_service: QuestionnaireService = Depends(get_questionnaire_service)
):
    """Get the number of basic questions."""
    try:
        return questionnaire_service.get_basic_questions_count()
    except Exception as e:
        logger.error(f"Error getting basic questions count: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

