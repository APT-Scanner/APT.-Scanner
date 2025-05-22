from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from src.models.schemas import UserFiltersCreate, UserFiltersUpdate, UserFiltersSchema
from src.models.database import get_db
from src.middleware.auth import get_current_user
from src.services import filters_service

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get(
    "/",
    response_model=UserFiltersSchema,
    summary="Get user filters",
    description="Retrieves the current user's filters."
)
async def get_filters(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Get the current user's filters.
    """
    user_id = current_user.firebase_uid
    logger.info(f"Fetching filters for user: {user_id}")
    
    try:
        filters = await filters_service.get_user_filters(db, user_id)
        
        if not filters:
            # If no filters exist, create default ones
            default_filters = UserFiltersCreate()
            filters = await filters_service.create_user_filters(db, user_id, default_filters)
            
        return filters
            
    except Exception as e:
        logger.error(f"Error fetching filters: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving filters."
        )

@router.post(
    "/",
    response_model=UserFiltersSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create user filters",
    description="Creates or replaces filters for the current user."
)
async def create_filters(
    filters_data: UserFiltersCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Create or replace filters for the current user.
    """
    user_id = current_user.firebase_uid
    logger.info(f"Creating filters for user: {user_id}")
    
    try:
        # Delete existing filters if any
        await filters_service.delete_user_filters(db, user_id)
        
        # Create new filters
        filters = await filters_service.create_user_filters(db, user_id, filters_data)
        return filters
            
    except Exception as e:
        logger.error(f"Error creating filters: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while creating filters."
        )

@router.put(
    "/",
    response_model=UserFiltersSchema,
    summary="Update user filters",
    description="Updates filters for the current user."
)
async def update_filters(
    filters_data: UserFiltersUpdate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Update filters for the current user.
    """
    user_id = current_user.firebase_uid
    logger.info(f"Updating filters for user: {user_id}")
    
    try:
        filters = await filters_service.update_user_filters(db, user_id, filters_data)
        
        if not filters:
            # This should never happen because update_user_filters creates filters if they don't exist
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Filters not found and could not be created."
            )
            
        return filters
            
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        
        logger.error(f"Error updating filters: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while updating filters."
        )

@router.delete(
    "/",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete user filters",
    description="Deletes filters for the current user."
)
async def delete_filters(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Delete filters for the current user.
    """
    user_id = current_user.firebase_uid
    logger.info(f"Deleting filters for user: {user_id}")
    
    try:
        await filters_service.delete_user_filters(db, user_id)
            
    except Exception as e:
        logger.error(f"Error deleting filters: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while deleting filters."
        ) 