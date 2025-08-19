"""Database configuration and session management."""
import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from typing import AsyncGenerator, Optional
import ssl

load_dotenv()

class Base(DeclarativeBase):
    pass

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable not set")

if DATABASE_URL.startswith("postgresql://") and not DATABASE_URL.startswith("postgresql+asyncpg://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")

# Don't create engine at import time for migration compatibility
engine: Optional[AsyncSession] = None
async_session_local: Optional[async_sessionmaker] = None

def get_engine():
    """Get or create the async engine."""
    global engine
    if engine is None:
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        # Supabase connection with SSL config and connection pooling
        engine = create_async_engine(
            DATABASE_URL, 
            echo=True,
            connect_args={"ssl": ssl_context},
            pool_size=20,
            max_overflow=0,
            pool_pre_ping=True,
            pool_recycle=3600  # Recycle connections every hour
        )
    return engine

def get_session_local():
    """Get or create the session maker."""
    global async_session_local
    if async_session_local is None:
        async_session_local = async_sessionmaker(
            bind=get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return async_session_local

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get database session."""
    session_local = get_session_local()
    async with session_local() as session:
        try:
            yield session
        finally:
            await session.close()