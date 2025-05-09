
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload 
from typing import List
import logging

from src.models.database import get_db
from src.models.models import Listing as ListingModel, Neighborhood as NeighborhoodModel
from src.models.schemas import ListingSchema 

logger = logging.getLogger(__name__)

router = APIRouter()

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

@router.get(
    "/all",
    response_model=List[ListingSchema],
    summary="Get all listings",
    description="Retrieves all listings from the database."
)
async def get_all_listings(db: AsyncSession = Depends(get_db), limit: int = 20):
    """
    Retrieves all listings from the database.
    """
    logger.info(f"Fetching all listings with limit: {limit}")

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

    try:
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
        .where(ListingModel.order_id == listing_id)
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
    