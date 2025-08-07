from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import and_
from typing import List
import logging
from src.database.postgresql_db import get_db
from src.database.models import Favorite, Listing, ListingMetadata
from src.database.schemas import FavoriteSchema
from src.middleware.auth import verify_firebase_user
from data.scrapers.yad2_scraper import is_listing_still_alive

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post(
    "/{listing_id}",
    response_model=FavoriteSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Add a listing to favorites"
)
async def add_favorites(
    listing_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(verify_firebase_user)
):
    """Add a listing to user's favorites"""
    user_id = current_user["user_id"]

    listing = await db.get(Listing, listing_id)
    if not listing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found")
    
    stmt = select(Favorite).where(and_(
        Favorite.user_id == user_id,
        Favorite.listing_id == listing.listing_id
    ))
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing:
        return existing
    
    new_favorite = Favorite(
        user_id=user_id,
        listing_id=listing.listing_id
    )

    db.add(new_favorite)
    await db.commit()
    await db.refresh(new_favorite)

    return new_favorite



@router.get(
    "/",
    response_model=List[FavoriteSchema],
    summary="Get user's favorites"
)
async def get_favorites(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(verify_firebase_user)
):
    """Get all favorites for the current user. Does not update listing status."""
    user_id = current_user["user_id"]
    
    stmt = (
        select(Favorite)
        .where(Favorite.user_id == user_id)
        .options(
            selectinload(Favorite.listing)
            .selectinload(Listing.listing_metadata).selectinload(ListingMetadata.neighborhood),
            selectinload(Favorite.listing)
            .selectinload(Listing.listing_metadata).selectinload(ListingMetadata.property_condition)
        )
    )
    
    result = await db.execute(stmt)
    favorites = result.scalars().all()
    return favorites


@router.put(
    "/status",
    response_model=List[FavoriteSchema],
    summary="Sync status of favorite listings",
    status_code=status.HTTP_200_OK
)
async def sync_favorites_status(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(verify_firebase_user)
):
    """
    Checks if favorited listings are still active and updates their status.
    Returns the updated list of favorites.
    """
    user_id = current_user["user_id"]
    
    # Join with ListingMetadata to get is_active status
    stmt = (
        select(Favorite)
        .join(Listing, Favorite.listing_id == Listing.listing_id)
        .join(ListingMetadata, Listing.listing_id == ListingMetadata.listing_id, isouter=True)
        .where(Favorite.user_id == user_id)
        .options(
            selectinload(Favorite.listing)
            .selectinload(Listing.listing_metadata).selectinload(ListingMetadata.neighborhood),
            selectinload(Favorite.listing)
            .selectinload(Listing.listing_metadata).selectinload(ListingMetadata.property_condition)
        )
    )
    
    result = await db.execute(stmt)
    favorites = result.scalars().all()
    
    updated = False
    for favorite in favorites:
        if favorite.listing:
            # Get the listing metadata to check is_active status
            metadata_stmt = select(ListingMetadata).where(
                ListingMetadata.listing_id == favorite.listing.listing_id
            )
            metadata_result = await db.execute(metadata_stmt)
            metadata = metadata_result.scalar_one_or_none()
            
            # We only check listings that are currently marked as active
            if metadata and metadata.is_active:
                if not is_listing_still_alive(favorite.listing.yad2_url_token):
                    metadata.is_active = False
                    updated = True
    
    if updated:
        await db.commit()
        # Refresh the objects to get the latest state after commit
        for favorite in favorites:
             await db.refresh(favorite)
             if favorite.listing:
                await db.refresh(favorite.listing)

    return favorites


@router.delete(
    "/{listing_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove from favorites"
)
async def remove_from_favorites(
    listing_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(verify_firebase_user)
):
    """Remove a listing from user's favorites"""
    user_id = current_user["user_id"]
    
    stmt = select(Favorite).where(
        and_(
            Favorite.user_id == user_id,
            Favorite.listing_id == listing_id
        )
    )
    
    result = await db.execute(stmt)
    favorite = result.scalar_one_or_none()
    
    if not favorite:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Favorite not found"
        )
    
    await db.delete(favorite)
    await db.commit()