"""Redis caching utilities for the application."""
import os
import json
import logging
from typing import Optional, Any, Dict
import redis
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Get Redis configuration from environment variables
REDIS_URL = "redis://" + os.getenv("REDIS_URL")
REDIS_ENABLED = os.getenv("REDIS_ENABLED", "false").lower() == "true"
CACHE_TTL = int(os.getenv("REDIS_CACHE_TTL", "3600"))  # Default: 1 hour

# Initialize Redis client if enabled
redis_client = None
if REDIS_ENABLED and REDIS_URL:
    try:
        redis_client = redis.from_url(REDIS_URL, decode_responses=True)
        logger.info("Redis caching is enabled")
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")
        redis_client = None
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
    if not redis_client:
        return None
        
    try:
        value = redis_client.get(key)
        if value:
            return json.loads(value)
        return None
    except Exception as e:
        logger.error(f"Error retrieving from Redis cache: {e}")
        return None

def set_cache(key: str, value: Dict[str, Any], ttl: int = CACHE_TTL) -> bool:
    """
    Set a value in Redis cache.
    
    Args:
        key: The cache key
        value: The value to cache (will be JSON serialized)
        ttl: Time to live in seconds
        
    Returns:
        True if successful, False otherwise
    """
    if not redis_client:
        return False
        
    try:
        serialized = json.dumps(value)
        print(f"Setting Redis cache for key: {key} with value: {serialized}")
        redis_client.set(key, serialized, ex=ttl)
        return True
    except Exception as e:
        logger.error(f"Error setting Redis cache: {e}")
        return False

def delete_cache(key: str) -> bool:
    """
    Delete a value from Redis cache.
    
    Args:
        key: The cache key to delete
        
    Returns:
        True if successful, False otherwise
    """
    if not redis_client:
        return False
        
    try:
        redis_client.delete(key)
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