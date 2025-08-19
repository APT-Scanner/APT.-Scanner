from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
import logging
from typing import List

from src.database.schemas import UserFiltersCreate, UserFiltersUpdate, UserFiltersSchema
from src.database.postgresql_db import get_db
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

@router.put(
    "/",
    response_model=UserFiltersSchema,
    status_code=status.HTTP_200_OK,
    summary="Create or update user filters",
    description="Creates new filters or updates existing ones for the current user."
)
async def create_or_update_filters(
    filters_data: UserFiltersUpdate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Create or update filters for the current user.
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
    
@router.get(
    "/cities",
    response_model=List[str],
    summary="Get all cities",
    description="Retrieves all available cities from the database."
)
async def get_cities(db: AsyncSession = Depends(get_db)):
    """
    Get all available cities.
    """
    try:
        cities = await filters_service.get_cities_list(db)
        return cities
    except Exception as e:
        logger.error(f"Error fetching cities: {e}")
        # Fallback to hardcoded list if database query fails
        return ["תל אביב יפו"]

@router.get(
    "/neighborhoods",
    response_model=List[str],
    summary="Get all neighborhoods names",
    description="Retrieves all neighborhoods names from the database."
)
async def get_neighborhoods(
    db: AsyncSession = Depends(get_db),
    city: str = None
):
    """
    Get all neighborhoods names for a specific city.
    """
    try:
        neighborhoods = await filters_service.get_neighborhoods_list(db, city)
        return neighborhoods
    except Exception as e:
        logger.error(f"Error fetching neighborhoods for city {city}: {e}")
        return []