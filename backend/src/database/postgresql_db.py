"""Database configuration and session management."""
import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
try:
    from sqlalchemy.ext.asyncio import async_sessionmaker
except ImportError:
    # Fallback for older SQLAlchemy versions
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy.orm import sessionmaker
    async_sessionmaker = sessionmaker
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import create_engine
from typing import AsyncGenerator, Optional, Any
import ssl

load_dotenv()

Base = declarative_base()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable not set")

if DATABASE_URL.startswith("postgresql://") and not DATABASE_URL.startswith("postgresql+asyncpg://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")

# Don't create engine at import time for migration compatibility
engine: Optional[AsyncSession] = None
async_session_local: Optional[Any] = None

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

# Synchronous database session for ETL operations
_sync_engine = None
_sync_session_local = None

def get_sync_engine():
    """Get or create the synchronous engine for ETL operations."""
    global _sync_engine
    if _sync_engine is None:
        # Convert async URL to sync URL
        sync_url = DATABASE_URL
        if sync_url.startswith("postgresql+asyncpg://"):
            sync_url = sync_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
        elif sync_url.startswith("postgresql://"):
            sync_url = sync_url.replace("postgresql://", "postgresql+psycopg2://")
        
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        _sync_engine = create_engine(
            sync_url,
            echo=False,  # Reduce logging for ETL operations
            connect_args={"sslmode": "require"},
            pool_size=10,
            max_overflow=0,
            pool_pre_ping=True,
            pool_recycle=3600
        )
    return _sync_engine

def get_sync_session_local():
    """Get or create the synchronous session maker for ETL operations."""
    global _sync_session_local
    if _sync_session_local is None:
        _sync_session_local = sessionmaker(
            bind=get_sync_engine(),
            expire_on_commit=False,
        )
    return _sync_session_local

def get_db_session():
    """Get synchronous database session for ETL operations."""
    session_local = get_sync_session_local()
    return session_local()