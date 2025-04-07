from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from src.models.models import User as UserModel
from src.models.schemas import UserCreate
from typing import Optional

async def get_user_by_firebase_uid(db: AsyncSession, firebase_uid: str) -> Optional[UserModel]:
    result = await db.execute(select(UserModel).filter(UserModel.firebase_uid == firebase_uid))
    return result.scalars().first()

async def create_user(db: AsyncSession, user_in: UserCreate) -> UserModel:
    db_user = UserModel(
        firebase_uid=user_in.firebase_uid, 
        email=user_in.email, 
        username=f"user_{user_in.firebase_uid[:8]}" 
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user

async def get_user(db: AsyncSession, user_id: int) -> Optional[UserModel]:
     result = await db.execute(select(UserModel).filter(UserModel.id == user_id))
     return result.scalars().first()
