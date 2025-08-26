from motor.motor_asyncio import AsyncIOMotorClient
from src.config.settings import settings
import logging

logger = logging.getLogger(__name__)

class MongoDatabase:
    client: AsyncIOMotorClient = None

db_client = MongoDatabase()

async def connect_to_mongo():
    """Establishes a connection to the MongoDB database."""
    logger.info("Connecting to MongoDB...")
    if not settings.MONGO_URL:
        logger.error("MONGO_URL not configured. MongoDB connection aborted.")
        return
        
    try:
        db_client.client = AsyncIOMotorClient(settings.MONGO_URL)
        # The ismaster command is cheap and does not require auth, used to check connection.
        await db_client.client.admin.command('ismaster')
        logger.info("MongoDB connection successful.")
    except Exception as e:
        logger.error(f"Could not connect to MongoDB: {e}")
        db_client.client = None


async def close_mongo_connection():
    """Closes the MongoDB database connection."""
    if db_client.client:
        logger.info("Closing MongoDB connection.")
        db_client.client.close()
        logger.info("MongoDB connection closed.")

def get_mongo_db():
    """
    Returns the application's default database instance from the client.
    Note: The database name should be part of the MONGO_URL.
    e.g., mongodb://user:pass@host:port/apt_scanner
    """
    if db_client.client:
        return db_client.client.get_database(settings.MONGO_DB_NAME)
    return None