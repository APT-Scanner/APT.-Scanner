from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update, delete, distinct
from src.database.models import UserFilters, Neighborhood
from src.database.schemas import UserFiltersCreate, UserFiltersUpdate
from typing import Optional, List
import logging

logger = logging.getLogger(__name__)

async def get_user_filters(db: AsyncSession, user_id: str) -> Optional[UserFilters]:
    """
    Get filters for a specific user
    """
    logger.debug(f"Fetching filters for user: {user_id}")
    result = await db.execute(select(UserFilters).filter(UserFilters.user_id == user_id))
    filters = result.scalars().first()
    logger.debug(f"Filters found: {filters is not None}")
    return filters

async def create_user_filters(db: AsyncSession, user_id: str, filters_data: UserFiltersCreate) -> UserFilters:
    """
    Create new filters for a user
    """
    logger.debug(f"Creating filters for user: {user_id}")
    
    # Convert options list to comma-separated string if it's a list
    options_str = None
    if hasattr(filters_data, 'options') and filters_data.options:
        if isinstance(filters_data.options, list):
            options_str = ','.join(filters_data.options)
        else:
            options_str = filters_data.options
    
    db_filters = UserFilters(
        user_id=user_id,
        type=filters_data.type,
        city=filters_data.city,
        neighborhood=filters_data.neighborhood,
        property_type=getattr(filters_data, 'property_type', None) if hasattr(filters_data, 'property_type') else None,
        price_min=filters_data.price_min,
        price_max=filters_data.price_max,
        rooms_min=filters_data.rooms_min,
        rooms_max=filters_data.rooms_max,
        size_min=filters_data.size_min,
        size_max=filters_data.size_max,
        options=options_str
    )
    
    db.add(db_filters)
    await db.commit()
    await db.refresh(db_filters)
    
    return db_filters

async def update_user_filters(db: AsyncSession, user_id: str, filters_data: UserFiltersUpdate) -> Optional[UserFilters]:
    """
    Update existing filters for a user
    """
    logger.debug(f"Updating filters for user: {user_id}")
    
    # Get existing filters
    filters = await get_user_filters(db, user_id)
    
    if not filters:
        # If no filters exist, create new ones
        return await create_user_filters(db, user_id, filters_data)
    
    # Convert options list to comma-separated string if it's a list
    options_str = None
    if hasattr(filters_data, 'options') and filters_data.options:
        if isinstance(filters_data.options, list):
            options_str = ','.join(filters_data.options)
        else:
            options_str = filters_data.options
    
    # Create a dictionary with only the fields that are not None
    update_data = {
        k: v for k, v in filters_data.model_dump().items() 
        if v is not None
    }
    
    # Handle options separately
    if options_str is not None:
        update_data['options'] = options_str
    
    if update_data:
        await db.execute(
            update(UserFilters)
            .where(UserFilters.user_id == user_id)
            .values(**update_data)
        )
        
        await db.commit()
        return await get_user_filters(db, user_id)
    
    return filters

async def delete_user_filters(db: AsyncSession, user_id: str) -> bool:
    """
    Delete filters for a user
    """
    logger.debug(f"Deleting filters for user: {user_id}")
    
    result = await db.execute(
        delete(UserFilters)
        .where(UserFilters.user_id == user_id)
    )
    
    await db.commit()
    
    # Return True if any row was deleted
    return result.rowcount > 0 

async def get_cities_list(db: AsyncSession) -> List[str]:
    """
    Get all available cities from neighborhoods
    """
    result = await db.execute(select(distinct(Neighborhood.city)).where(Neighborhood.city.isnot(None)))
    cities = result.scalars().all()
    return sorted(cities)

async def get_neighborhoods_list(db: AsyncSession, city: str) -> List[str]:
    """
    Get all neighborhoods names for a specific city
    """
    if not city:
        return []
        
    result = await db.execute(
        select(Neighborhood.hebrew_name)
        .where(Neighborhood.city == city)
        .order_by(Neighborhood.hebrew_name)
    )
    neighborhoods = result.scalars().all()
    return neighborhoods