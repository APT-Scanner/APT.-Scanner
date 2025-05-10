from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

import src.services.user_service as user_service
from src.models.schemas import User, UserCreate # Keep UserCreate if you need direct creation API
from src.models.database import get_db
from src.models.models import User as UserModel
from src.middleware.auth import get_current_user

router = APIRouter()

@router.get("/me", response_model=User)
async def read_users_me(current_user: UserModel = Depends(get_current_user)):
    """
    Get current authenticated user's details from the database.
    """
    return current_user

@router.post("/sync-profile", response_model=User, status_code=status.HTTP_200_OK)
async def sync_user_profile_after_registration(
    # The dependency handles everything: token verification, getting/creating user in DB
    current_user: UserModel = Depends(get_current_user)
):
    """
    Endpoint called by the frontend IMMEDIATELY after successful Firebase registration.
    Its main purpose is to ensure the user record exists in the local DB
    (handled by the get_current_active_user dependency) and potentially
    trigger any backend-specific post-registration logic.
    """
    #logger.info(f"Syncing profile for user ID: {current_user.id}, Firebase UID: {current_user.firebase_uid}")
    return current_user

@router.get("/{user_id}", response_model=User)
async def read_user_by_id(
    user_id: int,
    db: AsyncSession = Depends(get_db)
    # Optional: Add authentication if needed, e.g., check if current_user is admin
    # current_admin: UserModel = Depends(get_admin_user) # Example dependency
):
    """
    Get user details by their internal database ID.
    (Consider if this endpoint is needed and how to secure it).
    """
    db_user = await user_service.get_user(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return db_user


# Note: The original POST "/" endpoint might become redundant if user creation
# happens automatically via get_or_create_user_by_firebase triggered by
# get_current_active_user on the first authenticated request.
# Keep it if you need an explicit registration endpoint separate from login.
# If kept, decide if it needs authentication itself (e.g., maybe only admins can create users directly?).
# @router.post("/", response_model=User, status_code=status.HTTP_201_CREATED)
# async def create_user_endpoint(
#     user_in: UserCreate, # Schema might need adjustment if not using UserCreate anymore
#     db: AsyncSession = Depends(get_db)
# ):
#      # Logic might change depending on get_or_create flow
#      pass