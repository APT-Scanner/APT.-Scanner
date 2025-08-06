from fastapi import APIRouter, Depends, status

from src.database.schemas import User
from src.database.models import User as UserModel
from src.middleware.auth import get_current_user, get_or_create_current_user

router = APIRouter()

@router.get("/me", response_model=User)
async def read_users_me(current_user: UserModel = Depends(get_current_user)):
    """
    Get current authenticated user's details from the database.
    """
    return current_user

@router.post("/me", response_model=User, status_code=status.HTTP_201_CREATED)
async def create_current_user(
    current_user: UserModel = Depends(get_or_create_current_user)
):
    """
    Called by the frontend IMMEDIATELY after successful Firebase registration.
    Its main purpose is to ensure the user record exists in the local DB.
    """
    return current_user
