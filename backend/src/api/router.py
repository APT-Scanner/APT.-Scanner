from fastapi import APIRouter
from .v1.endpoints import users

# Main API router
api_router = APIRouter()

# Include all endpoints from v1
api_router.include_router(users.router, prefix="/v1/users", tags=["users"])
