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
        "http://localhost:5173",  # Frontend dev server
        "http://localhost:3000",  # Alternative frontend dev server
        "https://apt-scanner.com",  # Production
    ]

    # Database settings
    DB_NAME: str = os.getenv("DB_NAME", "apt_scanner")
    DB_USER: str = os.getenv("DB_USER", "postgres")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "postgres")
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: str = os.getenv("DB_PORT", "5432")
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )

    # Authentication settings
    SECRET_KEY: str = os.getenv("SECRET_KEY", "development_secret_key")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # Firebase settings
    FIREBASE_CREDENTIALS_PATH: str = os.getenv("FIREBASE_CREDENTIALS_PATH", "")

    # AI Model settings
    MODEL_PATH: str = os.getenv("MODEL_PATH", "../ai/models/latest")

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