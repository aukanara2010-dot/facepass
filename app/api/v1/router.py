from fastapi import APIRouter
from app.api.v1.endpoints import indexing

api_router = APIRouter()

# Include endpoint routers
api_router.include_router(indexing.router, tags=["facepass"])
