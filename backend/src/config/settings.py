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


    # Firebase settings
    FIREBASE_CREDENTIALS_PATH: str = os.getenv("FIREBASE_CREDENTIALS_PATH", "")


    # External API settings
    GOOGLE_MAPS_API_KEY: str = os.getenv("GOOGLE_MAPS_API_KEY", "")
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