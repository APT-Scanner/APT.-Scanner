from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from firebase_admin import auth
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict
import logging

from src.database.postgresql_db import get_db
from src.services import user_service 
from src.services.user_service import UserRegistrationError
from src.database.models import User as UserModel

logger = logging.getLogger(__name__)
security = HTTPBearer()

async def verify_firebase_user(token: HTTPAuthorizationCredentials = Depends(security)) -> Dict:
    """
    Verifies the Firebase ID token and returns the decoded token dictionary.
    Raises HTTPException if the token is invalid or expired.
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No credentials provided",
        )
    try:
        decoded_token = auth.verify_id_token(token.credentials)
        return decoded_token
    except auth.ExpiredIdTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except auth.InvalidIdTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not validate credentials: {e}",
        )

async def get_current_user(
    decoded_token: Dict = Depends(verify_firebase_user), 
    db: AsyncSession = Depends(get_db)
) -> UserModel:
    """
    Gets the user from the database based on the Firebase token.
    This is a read-only operation and will raise an exception if the user does not exist.
    """
    firebase_uid = decoded_token.get("uid")
    if not firebase_uid:
        raise HTTPException(status_code=400, detail="Firebase UID not found in token")

    user = await user_service.get_user_by_firebase_uid(db, firebase_uid=firebase_uid)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User not found in database. Registration may not be complete."
        )

    return user

async def get_or_create_current_user(
    decoded_token: Dict = Depends(verify_firebase_user),
    db: AsyncSession = Depends(get_db)
) -> UserModel:
    """
    Gets the decoded Firebase token, finds or creates the corresponding
    user in the local database, and returns the DB user model.
    To be used for user creation/sync endpoints.
    """
    firebase_uid = decoded_token.get("uid")
    if not firebase_uid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Invalid authentication token. Please try signing up again."
        )

    try:
        user = await user_service.get_or_create_user_by_firebase(
            db=db,
            firebase_uid=firebase_uid,
            email=decoded_token.get("email"),
            username=decoded_token.get("username")
        )

        if not user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                detail="Account creation failed due to an unexpected issue. Please try again."
            )

        return user
        
    except UserRegistrationError as e:
        # Convert user registration errors to appropriate HTTP exceptions
        error_code_map = {
            "EMAIL_ALREADY_EXISTS": status.HTTP_409_CONFLICT,
            "EMAIL_TOO_LONG": status.HTTP_400_BAD_REQUEST,
            "INVALID_FIREBASE_UID": status.HTTP_400_BAD_REQUEST,
            "DATABASE_CONNECTION_ERROR": status.HTTP_503_SERVICE_UNAVAILABLE,
            "DATABASE_CONFLICT": status.HTTP_409_CONFLICT,
            "DATABASE_ERROR": status.HTTP_500_INTERNAL_SERVER_ERROR,
            "USER_LOOKUP_ERROR": status.HTTP_500_INTERNAL_SERVER_ERROR,
            "UNKNOWN_ERROR": status.HTTP_500_INTERNAL_SERVER_ERROR
        }
        
        http_status = error_code_map.get(e.error_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        raise HTTPException(
            status_code=http_status,
            detail=e.message
        )
    except Exception as e:
        # Catch any other unexpected errors
        logger.error(f"Unexpected error in user creation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Account creation failed due to an unexpected error. Please try again."
        )