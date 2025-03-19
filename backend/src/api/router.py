from fastapi import APIRouter
from .v1.endpoints import users, neighborhoods, questionnaires, properties, recommendations

# Main API router
api_router = APIRouter()

# Include all endpoints from v1
api_router.include_router(users.router, prefix="/v1/users", tags=["users"])
api_router.include_router(neighborhoods.router, prefix="/v1/neighborhoods", tags=["neighborhoods"])
api_router.include_router(questionnaires.router, prefix="/v1/questionnaires", tags=["questionnaires"])
api_router.include_router(properties.router, prefix="/v1/properties", tags=["properties"])
api_router.include_router(recommendations.router, prefix="/v1/recommendations", tags=["recommendations"])