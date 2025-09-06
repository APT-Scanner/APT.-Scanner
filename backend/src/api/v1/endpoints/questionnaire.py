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

@router.post("/current/previous",
            response_model=NextQuestionResponse,
            summary="Go back to previous question")
async def go_to_previous_question(
    current_user: UserModel = Depends(get_current_user),
    questionnaire_service: QuestionnaireService = Depends(get_questionnaire_service)
):
    """Go back to the previous question by removing the last answer."""
    try:
        user_id = current_user.firebase_uid
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User ID not found")
            
        result = await questionnaire_service.go_back_to_previous_question(user_id)
        
        # Check if there was an error
        if 'error' in result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result['error']
            )
        
        return NextQuestionResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error going to previous question: {e}", exc_info=True)
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

@router.get("/responses",
            summary="Get user's questionnaire responses",
            description="Get all questions and user's current answers for editing")
async def get_user_questionnaire_responses(
    current_user: UserModel = Depends(get_current_user),
    questionnaire_service: QuestionnaireService = Depends(get_questionnaire_service),
    db: AsyncSession = Depends(get_db)
):
    """Get user's questionnaire responses and all available questions for editing."""
    try:
        user_id = current_user.firebase_uid
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User ID not found")
        
        # Get user's current responses
        user_responses = await questionnaire_service.get_user_responses(db, user_id)
        logger.info(f"User {user_id}: Retrieved {len(user_responses or {})} user responses for editing")
        
        # Get all questions from questionnaire service
        await questionnaire_service.load_questions()
        basic_questions = questionnaire_service.basic_information_questions
        dynamic_questions = questionnaire_service.dynamic_questionnaire
        
        # Combine all questions
        all_questions = {**basic_questions, **dynamic_questions}
        
        return {
            "user_responses": user_responses or {},
            "all_questions": all_questions,
            "basic_questions": basic_questions,
            "dynamic_questions": dynamic_questions
        }
        
    except Exception as e:
        logger.error(f"Error getting user questionnaire responses: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.put("/responses",
            summary="Update user's questionnaire responses",
            description="Update specific questionnaire answers for editing")
async def update_user_questionnaire_responses(
    request: QuestionnaireAnswersRequest,
    current_user: UserModel = Depends(get_current_user),
    questionnaire_service: QuestionnaireService = Depends(get_questionnaire_service),
    db: AsyncSession = Depends(get_db)
):
    """Update user's questionnaire responses for editing existing answers."""
    try:
        user_id = current_user.firebase_uid
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User ID not found")
        
        # Get user's current state
        user_state = await questionnaire_service.get_user_state(user_id)
        logger.info(f"User {user_id}: Current state has {len(user_state.get('answers', {}))} answers")
        
        # Log the answers being updated
        logger.info(f"User {user_id}: Updating answers for questions: {list(request.answers.keys())}")
        
        # Update the answers in the state
        for question_id, new_answer in request.answers.items():
            user_state['answers'][question_id] = new_answer
            
            # Add to answered questions if not already there
            if question_id not in user_state['answered_questions']:
                user_state['answered_questions'].append(question_id)
        
        logger.info(f"User {user_id}: After update, state has {len(user_state.get('answers', {}))} answers")
        
        # Save the updated state
        success = await questionnaire_service.update_user_state(user_id, user_state)
        
        if not success:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update responses")
        
        # Also update filters if questionnaire is completed
        completed_questionnaire = await questionnaire_service.get_completed_questionnaire(user_id)
        if completed_questionnaire:
            logger.info(f"User {user_id}: Found completed questionnaire, updating with {len(user_state['answers'])} answers")
            # Update the completed questionnaire in MongoDB as well
            update_result = await questionnaire_service.mongo_db.completed_questionnaires.update_one(
                {"user_id": user_id},
                {"$set": {"answers": user_state['answers']}}
            )
            logger.info(f"User {user_id}: Completed questionnaire update result: modified {update_result.modified_count} documents")
            
            # Update user filters based on the new answers if needed
            if questionnaire_service.db_session:
                await questionnaire_service._create_or_update_user_filters(user_id, user_state['answers'])
        else:
            logger.info(f"User {user_id}: No completed questionnaire found, only updating user state")
        
        return {
            "success": True,
            "message": "Responses updated successfully",
            "updated_questions": list(request.answers.keys())
        }
        
    except Exception as e:
        logger.error(f"Error updating user questionnaire responses: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.post("/reset-current-question",
            summary="Reset current question pointer for fresh start")
async def reset_current_question(
    current_user: UserModel = Depends(get_current_user),
    questionnaire_service: QuestionnaireService = Depends(get_questionnaire_service)
):
    """Reset the current_question_id to enable fresh start when answering more questions."""
    try:
        user_id = current_user.firebase_uid
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User ID not found")
        
        success = await questionnaire_service.reset_current_question(user_id)
        
        if not success:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to reset current question")
        
        return {"message": "Current question reset successfully", "success": True}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resetting current question: {e}", exc_info=True)
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

