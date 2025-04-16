from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import uvicorn
import logging
from datetime import datetime
import os
from pathlib import Path
from src.api.router import api_router
from src.config.settings import settings

# Ensure logs directory exists
Path("logs").mkdir(exist_ok=True)

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f"logs/api_{datetime.now().strftime('%Y%m%d')}.log")
    ]
)

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for the FastAPI application."""
    try:
        logger.info("Starting APT. Scanner API...")
        
        # Initialize Firebase Admin SDK if credentials are provided
        if settings.FIREBASE_CREDENTIALS_PATH:
            import firebase_admin
            from firebase_admin import credentials
            
            cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
            firebase_admin.initialize_app(cred)
            logger.info("Firebase Admin SDK initialized successfully")

        yield
        
    except Exception as e:
        logger.error(f"Error during startup: {str(e)}")
        raise
    finally:
        logger.info("Shutting down APT. Scanner API...")

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="API for the APT. Scanner application that helps users find the best-matched neighborhoods.",
    version="0.1.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom exception handler for HTTPException
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "status_code": exc.status_code
        }
    )

# Generic exception handler
@app.exception_handler(Exception)
async def generic_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "status_code": 500
        }
    )

# Include routers
app.include_router(api_router, prefix="/api")

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint to verify API status."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "0.1.0",
        "environment": os.getenv("ENVIRONMENT", "development")
    }

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level=settings.LOG_LEVEL.lower(),
        access_log=True
    )
