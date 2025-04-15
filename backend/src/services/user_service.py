from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from src.models.models import User as UserModel
from src.models.schemas import UserCreate 
from typing import Optional
import logging

logger = logging.getLogger(__name__)

async def get_user_by_firebase_uid(db: AsyncSession, firebase_uid: str) -> Optional[UserModel]:
    logger.debug(f"Attempting to fetch user by Firebase UID: {firebase_uid}")
    result = await db.execute(select(UserModel).filter(UserModel.firebase_uid == firebase_uid))
    user = result.scalars().first()
    logger.debug(f"User found: {user is not None}")
    return user

async def create_user(db: AsyncSession, firebase_uid: str, email: Optional[str] = None, username: Optional[str] = None) -> UserModel:
    """Creates a new user in the database."""
    logger.info(f"Creating new user for Firebase UID: {firebase_uid}")
    # Improved username generation (use provided name, email prefix, or fallback)
    if not username:
        username = email.split('@')[0] # Use email prefix as username

    db_user = UserModel(
        firebase_uid=firebase_uid,
        email=email,
        username=username
    )
    db.add(db_user)
    try:
        await db.commit()
        await db.refresh(db_user)
        logger.info(f"Successfully created user with ID: {db_user.id}")
        return db_user
    except Exception as e: 
        await db.rollback()
        logger.error(f"Error creating user: {e}")
        existing_user = await get_user_by_firebase_uid(db, firebase_uid)
        if existing_user:
            logger.warning("User likely created by concurrent request, returning existing user.")
            return existing_user
        raise # Re-raise other errors


async def get_or_create_user_by_firebase(db: AsyncSession, firebase_uid: str, email: Optional[str] = None, username: Optional[str] = None) -> UserModel:
    """
    Retrieves a user by Firebase UID. If the user doesn't exist,
    creates a new user record in the local database.
    """
    user = await get_user_by_firebase_uid(db, firebase_uid)
    if user:
        logger.debug(f"Found existing user ID {user.id} for Firebase UID {firebase_uid}")
        return user
    else:
        logger.info(f"No user found for Firebase UID {firebase_uid}. Creating new user.")
        return await create_user(db, firebase_uid=firebase_uid, email=email, username=username)


async def get_user(db: AsyncSession, user_id: int) -> Optional[UserModel]:
     logger.debug(f"Fetching user by internal ID: {user_id}")
     result = await db.execute(select(UserModel).filter(UserModel.id == user_id))
     user = result.scalars().first()
     logger.debug(f"User found: {user is not None}")
     return user

