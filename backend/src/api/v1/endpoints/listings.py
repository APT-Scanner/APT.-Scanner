from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload 
from typing import List
import logging
from datetime import datetime, timedelta
from sqlalchemy import and_, delete

from src.database.postgresql_db import get_db
from src.database.models import (
    Listing as ListingModel, 
    ListingMetadata as ListingMetadataModel,
    Neighborhood as NeighborhoodModel, 
    ViewHistory as ViewHistoryModel,
    Attribute,
    listing_attributes_association
)
from src.database.schemas import ListingSchema, ViewHistoryCreate, ViewHistorySchema, UserFiltersBase
from src.middleware.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get(
    "/",
    response_model=List[ListingSchema],
    summary="Get listings by filters",
    description="Retrieves listings from the database with optional filtering."
)
async def get_listings(
    db: AsyncSession = Depends(get_db), 
    limit: int = 20,
    current_user = Depends(get_current_user),
    filter_viewed: bool = True,
    filters: UserFiltersBase = Depends()
):
    """
    Retrieves all listings from the database with optional filtering.
    """
    logger.info(f"Fetching listings with filters: {filters.model_dump()}")
    
    try:
        # Join with ListingMetadata to access is_active and neighborhood info
        query = select(ListingModel).join(
            ListingMetadataModel, 
            ListingModel.listing_id == ListingMetadataModel.listing_id,
            isouter=True
        ).join(
            NeighborhoodModel,
            ListingMetadataModel.neighborhood_id == NeighborhoodModel.id,
            isouter=True
        )
        
        # Filter by active listings using ListingMetadata
        query = query.where(ListingMetadataModel.is_active == True)
        
        # Filter by city
        if filters.city and filters.city.strip():
            query = query.where(NeighborhoodModel.city == filters.city)
            
        # Filter by neighborhood name
        if filters.neighborhood and filters.neighborhood.strip():
            query = query.where(NeighborhoodModel.hebrew_name == filters.neighborhood)
        
        # Filter by property type
        if hasattr(filters, 'property_type') and filters.property_type and filters.property_type.strip():
            query = query.where(ListingModel.property_type == filters.property_type)
        
        # Price filters
        if hasattr(filters, 'price_min') and filters.price_min is not None:
            query = query.where(ListingModel.price >= filters.price_min)
        if hasattr(filters, 'price_max') and filters.price_max is not None:
            query = query.where(ListingModel.price <= filters.price_max)
        
        # Room count filters  
        if hasattr(filters, 'rooms_min') and filters.rooms_min is not None:
            query = query.where(ListingModel.rooms_count >= filters.rooms_min)
        if hasattr(filters, 'rooms_max') and filters.rooms_max is not None:
            query = query.where(ListingModel.rooms_count <= filters.rooms_max)
        
        # Size filters
        if hasattr(filters, 'size_min') and filters.size_min is not None:
            query = query.where(ListingModel.square_meter >= filters.size_min)
        if hasattr(filters, 'size_max') and filters.size_max is not None:
            query = query.where(ListingModel.square_meter <= filters.size_max)
        
        # Options/attributes filter with English-to-Hebrew mapping
        if filters.options and filters.options.strip():
                
            options_list = filters.options.split(',')
            english_options = [option.strip() for option in options_list if option.strip()]
            
            # Apply each option filter separately with proper joins
            for option in english_options:
                if option:
                    # Use subquery to avoid multiple joins on same table
                    # Use exact match for Hebrew attributes
                    attribute_subquery = (
                        select(listing_attributes_association.c.listing_id)
                        .select_from(
                            listing_attributes_association.join(
                                Attribute, 
                                Attribute.attribute_id == listing_attributes_association.c.attribute_id
                            )
                        )
                        .where(Attribute.attribute_name == option)
                    )
                    query = query.where(ListingModel.listing_id.in_(attribute_subquery))
        
        # Filter out recently viewed listings
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
            
            if recently_viewed_ids:
                query = query.where(~ListingModel.listing_id.in_(recently_viewed_ids))
        
        # Add relationships for complete listing data
        query = query.options(
            selectinload(ListingModel.images), 
            selectinload(ListingModel.attributes),
            selectinload(ListingModel.listing_metadata).selectinload(ListingMetadataModel.property_condition),
            selectinload(ListingModel.listing_metadata).selectinload(ListingMetadataModel.neighborhood).selectinload(NeighborhoodModel.metrics),
            selectinload(ListingModel.listing_metadata).selectinload(ListingMetadataModel.neighborhood).selectinload(NeighborhoodModel.meta_data)
        ).limit(limit)
        
        result = await db.execute(query)
        listings = result.scalars().all()
        
        logger.info(f"Found {len(listings)} listings matching the filters")
        return listings

    except Exception as e:
        logger.error(f"Database error while fetching filtered listings: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving listings."
        )

@router.post(
    "/views",
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
    Records when a user views a specific listing for recommendation tracking.
    """
    logger.info(f"Recording listing view for user: {current_user.firebase_uid}, listing: {view_data.listing_id}")
    
    try:
        # Check if listing exists
        listing_stmt = select(ListingModel).where(ListingModel.listing_id == view_data.listing_id)
        listing_result = await db.execute(listing_stmt)
        listing = listing_result.scalar_one_or_none()
        
        if not listing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Listing with ID {view_data.listing_id} not found"
            )
        
        # Create view history entry
        db_view = ViewHistoryModel(
            user_id=current_user.firebase_uid,
            listing_id=view_data.listing_id,
            viewed_at=datetime.now()
        )
        
        db.add(db_view)
        await db.commit()
        await db.refresh(db_view)
        
        logger.info(f"Successfully recorded view for listing {view_data.listing_id} by user {current_user.firebase_uid}")
        return db_view
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Database error while recording listing view: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while recording the view"
        )

@router.get(
    "/views",
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
    "/views",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Clear user's view history",
    description="Clears the user's listing view history."
)
async def clear_view_history(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Clears all view history for the current user.
    """
    logger.info(f"Clearing view history for user: {current_user.firebase_uid}")
    
    try:
        user_id = current_user.firebase_uid
        
        stmt = delete(ViewHistoryModel).where(ViewHistoryModel.user_id == user_id)
        result = await db.execute(stmt)
        await db.commit()
        
        logger.info(f"Cleared {result.rowcount} view history entries for user {user_id}")
        
    except Exception as e:
        await db.rollback()
        logger.error(f"Database error while clearing view history: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while clearing view history"
        )

@router.get(
    "/{listing_id}",
    response_model=ListingSchema,
    summary="Get listing by ID"
)
async def get_listing_by_id(
    listing_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific listing by ID"""
    logger.info(f"Fetching listing with ID: {listing_id}")
    
    stmt = (
        select(ListingModel)
        .where(ListingModel.listing_id == listing_id)
        .options(
            selectinload(ListingModel.images),
            selectinload(ListingModel.attributes),
            selectinload(ListingModel.listing_metadata).selectinload(ListingMetadataModel.property_condition),
            selectinload(ListingModel.listing_metadata).selectinload(ListingMetadataModel.neighborhood).selectinload(NeighborhoodModel.metrics),
            selectinload(ListingModel.listing_metadata).selectinload(ListingMetadataModel.neighborhood).selectinload(NeighborhoodModel.meta_data)
        )
    )
    
    try:
        result = await db.execute(stmt)
        listing = result.scalar_one_or_none()
        
        if not listing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Listing with ID {listing_id} not found"
            )
            
        return listing
        
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        logger.error(f"Database error while fetching listing {listing_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving the listing"
        )
    