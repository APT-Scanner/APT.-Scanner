"""Redis caching utilities for the application."""
import os
import json
import logging
from typing import Optional, Any, Dict
import redis
from dotenv import load_dotenv
from collections import deque
from bson import ObjectId
from datetime import datetime

load_dotenv()

logger = logging.getLogger(__name__)

# Get Redis configuration from environment variables
REDIS_ENABLED = os.getenv("REDIS_ENABLED", "false").lower() == "true"
CACHE_TTL = int(os.getenv("REDIS_CACHE_TTL", "3600"))  # Default: 1 hour
REDIS_HOST = os.getenv("REDIS_HOST")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_USERNAME = os.getenv("REDIS_USERNAME")
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")

class CustomJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder to handle special types."""
    def default(self, o):
        if isinstance(o, deque):
            return list(o)
        if isinstance(o, ObjectId):
            return str(o)
        if isinstance(o, datetime):
            return o.isoformat()
        return json.JSONEncoder.default(self, o)

def _create_redis_client():
    """Create and return a Redis client instance."""
    if not REDIS_ENABLED or not REDIS_HOST or not REDIS_PORT or not REDIS_USERNAME or not REDIS_PASSWORD:
        return None
    
    try:
        client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            decode_responses=True,
            username=REDIS_USERNAME,
            password=REDIS_PASSWORD,
        )
        client.ping()
        logger.info("Redis connection successful")
        return client
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")
        return None

def _get_redis_client():
    """Get Redis client with automatic reconnection."""
    global redis_client
    
    if redis_client is None:
        redis_client = _create_redis_client()
    
    # Test connection and reconnect if needed
    if redis_client:
        try:
            redis_client.ping()
        except Exception as e:
            logger.warning(f"Redis connection lost, attempting to reconnect: {e}")
            redis_client = _create_redis_client()
    
    return redis_client

# Initialize Redis client if enabled
redis_client = None
if REDIS_ENABLED and REDIS_HOST and REDIS_PORT and REDIS_USERNAME and REDIS_PASSWORD:
    redis_client = _create_redis_client()
else:
    logger.info("Redis caching is disabled")

def get_cache(key: str) -> Optional[Dict[str, Any]]:
    """
    Get a value from Redis cache.
    
    Args:
        key: The cache key to retrieve
        
    Returns:
        The cached value as a dictionary or None if not found/error
    """
    client = _get_redis_client()
    if not client:
        return None
        
    try:
        value = client.get(key)
        if value:
            return json.loads(value)
        return None
    except Exception as e:
        logger.error(f"Error retrieving from Redis cache: {e}")
        return None

def set_cache(key: str, value: Dict[str, Any], ttl: int = CACHE_TTL) -> bool:
    """
    Set a value in Redis cache using a custom encoder.
    
    Args:
        key: The cache key
        value: The value to cache (will be JSON serialized)
        ttl: Time to live in seconds
        
    Returns:
        True if successful, False otherwise
    """
    client = _get_redis_client()
    if not client:
        return False
        
    try:
        # Use the custom encoder to handle special types
        serialized = json.dumps(value, cls=CustomJSONEncoder)
        client.set(key, serialized, ex=ttl)
        return True
    except Exception as e:
        logger.error(f"Error setting Redis cache: {e}", exc_info=True)
        return False

def delete_cache(key: str) -> bool:
    """
    Delete a value from Redis cache.
    
    Args:
        key: The cache key to delete
        
    Returns:
        True if successful, False otherwise
    """
    client = _get_redis_client()
    if not client:
        return False
        
    try:
        client.delete(key)
        return True
    except Exception as e:
        logger.error(f"Error deleting from Redis cache: {e}")
        return False

def get_questionnaire_cache_key(user_id: str) -> str:
    """
    Generate a standard Redis key for questionnaire data.
    
    Args:
        user_id: The user's ID
        
    Returns:
        A formatted Redis key string
    """
    return f"questionnaire:{user_id}"