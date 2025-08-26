from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import uvicorn
import logging
from src.api.router import api_router
from src.config.settings import settings
from src.database.mongo_db import connect_to_mongo, close_mongo_connection


# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for the FastAPI application."""
    try:
        logger.info("Starting APT. Scanner API...")
        
        # Connect to MongoDB
        await connect_to_mongo()
        
        if settings.FIREBASE_CREDENTIALS:
            import firebase_admin
            from firebase_admin import credentials
            import json
            import base64
            
            try:
                decoded_credentials = base64.b64decode(settings.FIREBASE_CREDENTIALS).decode('utf-8')
                credentials_dict = json.loads(decoded_credentials)
                
                cred = credentials.Certificate(credentials_dict)
                firebase_admin.initialize_app(cred)
                logger.info("Firebase Admin SDK initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Firebase Admin SDK: {str(e)}")
        else:
            logger.error("FIREBASE_SERVICE_ACCOUNT_JSON_BASE64 environment variable is not set! Firebase authentication will not work.")

        yield
        
    except Exception as e:
        logger.error(f"Error during startup: {str(e)}")
        raise
    finally:
        logger.info("Shutting down APT. Scanner API...")
        # Disconnect from MongoDB
        await close_mongo_connection()

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="API for the APT. Scanner application that helps users find the best-matched neighborhoods.",
    version="0.1.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins= settings.CORS_ORIGINS,
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
@app.get("/", status_code=status.HTTP_200_OK, tags=["Health Check"])
def health_check():
    """
    Endpoint for Elastic Beanstalk health checks.
    """
    return {"status": "ok", "message": "APT. Scanner API is healthy"}

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level=settings.LOG_LEVEL.lower(),
        access_log=True
    )