from fastapi import APIRouter
from .v1.endpoints import users, listings, favorites, questionnaire, filters


# Main API router
api_router = APIRouter()

# Include all endpoints from v1
api_router.include_router(users.router, prefix="/v1/users", tags=["users"])
api_router.include_router(listings.router, prefix = "/v1/listings", tags=["listings"])
api_router.include_router(favorites.router, prefix = "/v1/favorites", tags=["favorites"])
api_router.include_router(questionnaire.router, prefix = "/v1/questionnaire", tags=["questionnaire"])
api_router.include_router(filters.router, prefix = "/v1/filters", tags=["filters"])



