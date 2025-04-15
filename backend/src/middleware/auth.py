
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from firebase_admin import auth
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Dict

from src.models.database import get_db
from src.services import user_service # ייבוא שירות המשתמשים
from src.models.models import User as UserModel # ייבוא מודל המשתמש

# HTTPBearer scheme
security = HTTPBearer()

# Dependency to verify Firebase token and return decoded token
async def get_current_firebase_user(token: HTTPAuthorizationCredentials = Depends(security)) -> Dict:
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
        # Verify the token against the Firebase Auth API
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
        # Catch other potential errors during verification
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not validate credentials: {e}",
        )

# Dependency to get the corresponding local DB user (and create if not exists)
async def get_current_active_user(
    decoded_token: Dict = Depends(get_current_firebase_user), 
    db: AsyncSession = Depends(get_db)) -> UserModel:
    """
    Gets the decoded Firebase token, finds or creates the corresponding
    user in the local database, checks if active, and returns the DB user model.
    """
    firebase_uid = decoded_token.get("uid")
    if not firebase_uid:
         raise HTTPException(status_code=400, detail="Firebase UID not found in token")

    user = await user_service.get_or_create_user_by_firebase(
        db=db,
        firebase_uid=firebase_uid,
        email=decoded_token.get("email"),
        username=decoded_token.get("username")
    )

    if not user:
         raise HTTPException(status_code=404, detail="User mapping not found or could not be created.")

    return user