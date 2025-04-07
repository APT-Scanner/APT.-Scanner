from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

import src.services.user_service as user_service 
from src.models.schemas import User, UserCreate 
from src.models.database import get_db 
# from auth.firebase_auth import get_current_user # נוסיף בהמשך

router = APIRouter()

@router.post("/", response_model=User, status_code=status.HTTP_201_CREATED)
async def create_user_endpoint(
    user_in: UserCreate, 
    db: AsyncSession = Depends(get_db)
):
    existing_user = await user_service.get_user_by_firebase_uid(db, firebase_uid=user_in.firebase_uid)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="User with this Firebase UID already exists in the system."
        )
    try:
        created_user = await user_service.create_user(db=db, user_in=user_in)
        return created_user
    except Exception as e: # תפוס שגיאות ספציפיות יותר אם אפשר
         raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/{user_id}", response_model=User)
async def read_user_endpoint(
    user_id: int, 
    db: AsyncSession = Depends(get_db)
    # current_user: User = Depends(get_current_user) # נוסיף בהמשך להגנה
):
    db_user = await user_service.get_user(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return db_user

# Endpoint עתידי לדוגמה שישתמש באימות
# @router.get("/me", response_model=User)
# async def read_current_user_endpoint(
#     current_user_from_auth: dict = Depends(get_current_user), # יחזיר נתונים מ-Firebase
#     db: AsyncSession = Depends(get_db)
# ):
#     # השתמש ב-firebase_uid מהאימות כדי למצוא/ליצור את המשתמש ב-DB
#     firebase_uid = current_user_from_auth.get("uid")
#     user = await user_service.get_or_create_user(db, firebase_uid=firebase_uid, email=current_user_from_auth.get("email"))
#     if user is None:
#          raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Could not find or create user mapping.")
#     return user