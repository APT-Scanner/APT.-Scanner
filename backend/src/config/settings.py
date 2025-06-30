import os
from typing import List
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Settings(BaseSettings):
    # API settings
    API_V1_STR: str = "/v1"
    PROJECT_NAME: str = "APT. Scanner"

    # CORS settings
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",# Frontend dev server
        "http://localhost:5174",  
        "http://localhost:3000",  # Alternative frontend dev server
        "http://192.168.1.204:5173",  # Local frontend dev server
        "https://apt-scanner.com",  # Production
    ]

    # Database settings
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL"
    )
    MONGO_URL: str = os.getenv("MONGO_URL", "")
    MONGO_DB_NAME: str = os.getenv("MONGO_DB_NAME", "")
    
    # Redis settings
    REDIS_ENABLED: bool = os.getenv("REDIS_ENABLED", "false").lower() == "true"
    REDIS_CACHE_TTL: int = int(os.getenv("REDIS_CACHE_TTL", "3600"))
    REDIS_HOST: str = os.getenv("REDIS_HOST", "")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_USERNAME: str = os.getenv("REDIS_USERNAME", "")
    REDIS_PASSWORD: str = os.getenv("REDIS_PASSWORD", "")

    # Firebase settings
    FIREBASE_CREDENTIALS: str = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON_BASE64", "")


    # External API settings
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")

    # Scraper settings
    SCRAPER_API_USERNAME: str = os.getenv("SCRAPER_API_USERNAME", "")
    SCRAPER_API_PASSWORD: str = os.getenv("SCRAPER_API_PASSWORD", "")
    SCRAPEOWL_API_KEY: str = os.getenv("SCRAPEOWL_API_KEY", "")

    # Logging settings
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    class Config:
        case_sensitive = True
        env_file = ".env"
        extra = "ignore"  # This will ignore any extra fields not defined in the model

# Create settings instance
settings = Settings()