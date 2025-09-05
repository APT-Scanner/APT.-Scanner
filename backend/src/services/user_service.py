from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from src.database.models import User as UserModel
from src.database.schemas import UserCreate 
from typing import Optional, Dict, Any
import logging
import uuid
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)

class UserRegistrationError(Exception):
    """Custom exception for user registration errors with user-friendly messages."""
    def __init__(self, message: str, error_code: str = None, original_error: Exception = None):
        self.message = message
        self.error_code = error_code
        self.original_error = original_error
        super().__init__(self.message)

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
    """
    Creates a new user in the database with a unique username.
    Raises UserRegistrationError with user-friendly messages on failure.
    """
    logger.info(f"Creating new user for Firebase UID: {firebase_uid}")
    
    # Validate inputs
    if not firebase_uid or firebase_uid.strip() == "":
        raise UserRegistrationError(
            "Invalid user authentication. Please try signing up again.",
            error_code="INVALID_FIREBASE_UID"
        )
    
    if email and len(email) > 255:
        raise UserRegistrationError(
            "Email address is too long. Please use a shorter email address.",
            error_code="EMAIL_TOO_LONG"
        )
    
    # Generate base username
    if not username:
        if email:
            base_username = email.split('@')[0]
        else:
            base_username = f"user_{firebase_uid[:8]}"
    else:
        base_username = username
    
    # Validate username length
    if len(base_username) > 45:  # Leave room for uniqueness suffix
        base_username = base_username[:45]
    
    try:
        # Ensure username is unique
        unique_username = await generate_unique_username(db, base_username)
        
        # Create user model
        db_user = UserModel(
            firebase_uid=firebase_uid,
            email=email,
            username=unique_username
        )
        db.add(db_user)
        
        # Attempt to save to database
        await db.commit()
        await db.refresh(db_user)
        logger.info(f"Successfully created user with ID: {db_user.id} and username: {unique_username}")
        return db_user
        
    except IntegrityError as e:
        await db.rollback()
        logger.error(f"IntegrityError creating user: {e}")
        
        # Check if it's a duplicate Firebase UID (concurrent request)
        existing_user = await get_user_by_firebase_uid(db, firebase_uid)
        if existing_user:
            logger.warning("User already exists, likely created by concurrent request")
            return existing_user
        
        # Check if it's an email conflict
        if email and "email" in str(e).lower():
            raise UserRegistrationError(
                "This email address is already registered. If this is your account, try signing in instead.",
                error_code="EMAIL_ALREADY_EXISTS",
                original_error=e
            )
        
        # Try once more with UUID suffix for username conflicts
        logger.warning("Username conflict detected, retrying with unique suffix")
        try:
            fallback_username = f"{base_username}_{uuid.uuid4().hex[:8]}"
            
            db_user = UserModel(
                firebase_uid=firebase_uid,
                email=email,
                username=fallback_username
            )
            db.add(db_user)
            await db.commit()
            await db.refresh(db_user)
            logger.info(f"Successfully created user with fallback username: {fallback_username}")
            return db_user
            
        except IntegrityError as retry_error:
            await db.rollback()
            logger.error(f"Failed to create user even with fallback username: {retry_error}")
            if email and "email" in str(retry_error).lower():
                raise UserRegistrationError(
                    "This email address is already registered. If this is your account, try signing in instead.",
                    error_code="EMAIL_ALREADY_EXISTS",
                    original_error=retry_error
                )
            else:
                raise UserRegistrationError(
                    "Unable to create your account due to a database conflict. Please try again or contact support if the problem persists.",
                    error_code="DATABASE_CONFLICT",
                    original_error=retry_error
                )
        except Exception as retry_error:
            await db.rollback()
            logger.error(f"Unexpected error on retry: {retry_error}")
            raise UserRegistrationError(
                "Account creation failed due to a technical issue. Please try again in a few moments.",
                error_code="DATABASE_ERROR",
                original_error=retry_error
            )
            
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"Database error creating user: {e}")
        raise UserRegistrationError(
            "We're experiencing database issues. Please try creating your account again in a few minutes.",
            error_code="DATABASE_CONNECTION_ERROR",
            original_error=e
        )
    except Exception as e:
        await db.rollback()
        logger.error(f"Unexpected error creating user: {e}")
        raise UserRegistrationError(
            "Account creation failed due to an unexpected error. Please try again or contact support if the problem continues.",
            error_code="UNKNOWN_ERROR",
            original_error=e
        )


async def get_or_create_user_by_firebase(db: AsyncSession, firebase_uid: str, email: Optional[str] = None, username: Optional[str] = None) -> UserModel:
    """
    Retrieves a user by Firebase UID. If the user doesn't exist,
    creates a new user record in the local database.
    Raises UserRegistrationError with user-friendly messages on failure.
    """
    try:
        user = await get_user_by_firebase_uid(db, firebase_uid)
        if user:
            logger.debug(f"Found existing user ID {user.id} for Firebase UID {firebase_uid}")
            return user
        else:
            logger.info(f"No user found for Firebase UID {firebase_uid}. Creating new user.")
            return await create_user(db, firebase_uid=firebase_uid, email=email, username=username)
    except UserRegistrationError:
        # Re-raise user registration errors as-is
        raise
    except Exception as e:
        logger.error(f"Unexpected error in get_or_create_user_by_firebase: {e}")
        raise UserRegistrationError(
            "Unable to complete account setup. Please try again or contact support if the problem persists.",
            error_code="USER_LOOKUP_ERROR",
            original_error=e
        )


async def get_user(db: AsyncSession, user_id: int) -> Optional[UserModel]:
     logger.debug(f"Fetching user by internal ID: {user_id}")
     result = await db.execute(select(UserModel).filter(UserModel.id == user_id))
     user = result.scalars().first()
     logger.debug(f"User found: {user is not None}")
     return user

