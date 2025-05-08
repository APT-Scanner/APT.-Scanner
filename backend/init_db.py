"""Initialize the database by creating all tables."""
import asyncio
from src.models.database import Base, engine
from src.models.models import *  # Import all models to register them with Base

async def init_db():
    """Create all tables."""
    print("Creating tables...")
    async with engine.begin() as conn:
        # Drop all existing tables
        # await conn.run_sync(Base.metadata.drop_all)
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)
    print("Tables created successfully!")

if __name__ == "__main__":
    asyncio.run(init_db()) 