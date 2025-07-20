from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError
from src.database.models import User as UserModel
from src.database.schemas import UserCreate 
from typing import Optional
import logging
import uuid

logger = logging.getLogger(__name__)

async def get_user_by_firebase_uid(db: AsyncSession, firebase_uid: str) -> Optional[UserModel]:
    logger.debug(f"Attempting to fetch user by Firebase UID: {firebase_uid}")
    result = await db.execute(select(UserModel).filter(UserModel.firebase_uid == firebase_uid))
    user = result.scalars().first()
    logger.debug(f"User found: {user is not None}")
    return user

async def get_user_by_username(db: AsyncSession, username: str) -> Optional[UserModel]:
    """Check if a username already exists in the database."""
    result = await db.execute(select(UserModel).filter(UserModel.username == username))
    return result.scalars().first()

async def generate_unique_username(db: AsyncSession, base_username: str) -> str:
    """Generate a unique username by appending numbers if the base username is taken."""
    username = base_username
    counter = 1
    
    while await get_user_by_username(db, username):
        username = f"{base_username}_{counter}"
        counter += 1
        # Safety check to prevent infinite loops
        if counter > 9999:
            username = f"{base_username}_{uuid.uuid4().hex[:8]}"
            break
    
    return username

async def create_user(db: AsyncSession, firebase_uid: str, email: Optional[str] = None, username: Optional[str] = None) -> UserModel:
    """Creates a new user in the database with a unique username."""
    logger.info(f"Creating new user for Firebase UID: {firebase_uid}")
    
    # Generate base username
    if not username:
        if email:
            base_username = email.split('@')[0]
        else:
            base_username = f"user_{firebase_uid[:8]}"
    else:
        base_username = username
    
    # Ensure username is unique
    unique_username = await generate_unique_username(db, base_username)
    
    db_user = UserModel(
        firebase_uid=firebase_uid,
        email=email,
        username=unique_username
    )
    db.add(db_user)
    
    try:
        await db.commit()
        await db.refresh(db_user)
        logger.info(f"Successfully created user with ID: {db_user.id} and username: {unique_username}")
        return db_user
    except IntegrityError as e:
        await db.rollback()
        logger.error(f"IntegrityError creating user: {e}")
        
        # Check if user was created by concurrent request with same firebase_uid
        existing_user = await get_user_by_firebase_uid(db, firebase_uid)
        if existing_user:
            logger.warning("User likely created by concurrent request, returning existing user.")
            return existing_user
        
        # If it's still a username conflict (race condition), try one more time with UUID
        logger.warning("Username conflict detected, retrying with UUID suffix")
        fallback_username = f"{base_username}_{uuid.uuid4().hex[:8]}"
        
        db_user = UserModel(
            firebase_uid=firebase_uid,
            email=email,
            username=fallback_username
        )
        db.add(db_user)
        
        try:
            await db.commit()
            await db.refresh(db_user)
            logger.info(f"Successfully created user with fallback username: {fallback_username}")
            return db_user
        except Exception as retry_error:
            await db.rollback()
            logger.error(f"Failed to create user even with fallback username: {retry_error}")
            raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Unexpected error creating user: {e}")
        raise


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

