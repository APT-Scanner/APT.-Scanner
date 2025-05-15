from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload 
from typing import List
import logging
from datetime import datetime, timedelta
from sqlalchemy import and_, delete

from src.models.database import get_db
from src.models.models import Listing as ListingModel, Neighborhood as NeighborhoodModel, ViewHistory as ViewHistoryModel
from src.models.schemas import ListingSchema, ViewHistoryCreate, ViewHistorySchema
from src.middleware.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get(
    "/all",
    response_model=List[ListingSchema],
    summary="Get all listings",
    description="Retrieves all listings from the database."
)
async def get_all_listings(
    db: AsyncSession = Depends(get_db), 
    limit: int = 20,
    current_user = Depends(get_current_user),
    filter_viewed: bool = True
):
    """
    Retrieves all listings from the database, optionally filtering out recently viewed listings.
    """
    logger.info(f"Fetching all listings with limit: {limit}")
    
    try:
        if filter_viewed:
            one_week_ago = datetime.now() - timedelta(days=7)
            
            user_id = current_user.firebase_uid
            
            viewed_stmt = (
                select(ViewHistoryModel.listing_id)
                .where(and_(
                    ViewHistoryModel.user_id == user_id,  
                    ViewHistoryModel.viewed_at >= one_week_ago
                ))
            )
            
            result = await db.execute(viewed_stmt)
            recently_viewed_ids = [row[0] for row in result.all()]
            
            stmt = (
                select(ListingModel)
                .where(~ListingModel.order_id.in_(recently_viewed_ids) if recently_viewed_ids else True)
                .options(
                    selectinload(ListingModel.neighborhood),
                    selectinload(ListingModel.property_condition), 
                    selectinload(ListingModel.images), 
                    selectinload(ListingModel.tags) 
                )
                .limit(limit)
            )
        else:
            stmt = (
                select(ListingModel)
                .options(
                    selectinload(ListingModel.neighborhood),
                    selectinload(ListingModel.property_condition), 
                    selectinload(ListingModel.images), 
                    selectinload(ListingModel.tags) 
                )
                .limit(limit)
            )

        result = await db.execute(stmt)
        listings = result.scalars().all()
        return listings

    except Exception as e:
        logger.error(f"Database error while fetching all listings: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving listings."
        )

@router.get(
    "/by-neighborhood/{neighborhood_id}",
    response_model=List[ListingSchema], 
    summary="Get listings by neighborhood ID",
    description="Retrieves all listings associated with a specific neighborhood ID (yad2_hood_id)."
)
async def get_listings_by_neighborhood(
    neighborhood_id: int,
    db: AsyncSession = Depends(get_db) 
):
    """
    Retrieves listings from the database filtered by the provided neighborhood ID.
    """
    logger.info(f"Fetching listings for neighborhood_id: {neighborhood_id}")

    neighborhood = await db.get(NeighborhoodModel, neighborhood_id)
    if not neighborhood:
        logger.warning(f"Neighborhood with id {neighborhood_id} not found.")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Neighborhood with id {neighborhood_id} not found"
        )

    stmt = (
        select(ListingModel)
        .where(ListingModel.neighborhood_id == neighborhood_id)
        .options(
            selectinload(ListingModel.neighborhood),
            selectinload(ListingModel.property_condition), 
            selectinload(ListingModel.images), 
            selectinload(ListingModel.tags) 
        )
    )

    try:
        result = await db.execute(stmt)
        listings = result.scalars().all()
        logger.info(f"Found {len(listings)} listings for neighborhood_id: {neighborhood_id}")
        return listings 

    except Exception as e:
        logger.error(f"Database error while fetching listings for neighborhood {neighborhood_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving listings."
        )

@router.post(
    "/view",
    response_model=ViewHistorySchema,
    summary="Record a listing view",
    description="Records when a user views a listing."
)
async def record_listing_view(
    view_data: ViewHistoryCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Records when a user views a listing to prevent showing it again for a day.
    """
    logger.info(f"Recording view for listing ID: {view_data.listing_id} by user {current_user}")
    
    try:
        stmt = select(ListingModel).where(ListingModel.order_id == view_data.listing_id)
        result = await db.execute(stmt)
        listing = result.scalar_one_or_none()
        
        if not listing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Listing with ID {view_data.listing_id} not found"
            )
            
        user_id = current_user.firebase_uid
        
        one_day_ago = datetime.now() - timedelta(days=1)
        existing_view_stmt = (
            select(ViewHistoryModel)
            .where(and_(
                ViewHistoryModel.user_id == user_id,  
                ViewHistoryModel.listing_id == view_data.listing_id,
                ViewHistoryModel.viewed_at >= one_day_ago
            ))
        )
        
        existing_result = await db.execute(existing_view_stmt)
        existing_view = existing_result.scalar_one_or_none()
        
        if existing_view:
            existing_view.viewed_at = datetime.now()
            await db.commit()
            return existing_view
        
        new_view = ViewHistoryModel(
            user_id=user_id,  
            listing_id=view_data.listing_id
        )
        
        db.add(new_view)
        await db.commit()
        await db.refresh(new_view)
        
        return new_view
            
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        logger.error(f"Database error while recording view: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while recording the view"
        )

@router.get(
    "/view-history",
    response_model=List[ViewHistorySchema],
    summary="Get user's view history",
    description="Retrieves the user's listing view history."
)
async def get_view_history(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
    limit: int = 50
):
    """
    Retrieves the user's listing view history.
    """
    logger.info(f"Fetching view history for user: {current_user}")
    
    try:
        user_id = current_user.firebase_uid
        
        stmt = (
            select(ViewHistoryModel)
            .where(ViewHistoryModel.user_id == user_id)  
            .order_by(ViewHistoryModel.viewed_at.desc())
            .limit(limit)
        )
        
        result = await db.execute(stmt)
        view_history = result.scalars().all()
        
        return view_history
            
    except Exception as e:
        logger.error(f"Database error while fetching view history: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving view history"
        )

@router.delete(
    "/view-history/clear",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Clear user's view history",
    description="Clears the user's listing view history."
)
async def clear_view_history(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Clears the user's listing view history.
    """
    logger.info(f"Clearing view history for user: {current_user}")
    
    try:
        user_id = current_user.firebase_uid
        
        stmt = (
            delete(ViewHistoryModel)
            .where(ViewHistoryModel.user_id == user_id) 
        )
        
        await db.execute(stmt)
        await db.commit()
            
    except Exception as e:
        logger.error(f"Database error while clearing view history: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while clearing view history"
        )

@router.get(
    "/{order_id}",
    response_model=ListingSchema,
    summary="Get listing by ID"
)
async def get_listing_by_id(
    order_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific listing by ID"""
    logger.info(f"Fetching listing with ID: {order_id}")
    
    stmt = (
        select(ListingModel)
        .where(ListingModel.order_id == order_id)
        .options(
            selectinload(ListingModel.neighborhood),
            selectinload(ListingModel.property_condition),
            selectinload(ListingModel.images),
            selectinload(ListingModel.tags)
        )
    )
    
    try:
        result = await db.execute(stmt)
        listing = result.scalar_one_or_none()
        
        if not listing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Listing with ID {order_id} not found"
            )
            
        return listing
        
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        logger.error(f"Database error while fetching listing {order_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving the listing"
        )
    