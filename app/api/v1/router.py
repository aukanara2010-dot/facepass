from fastapi import APIRouter
from app.api.v1.endpoints import health, faces, events, sessions, indexing

api_router = APIRouter()

# Include endpoint routers
api_router.include_router(health.router, tags=["health"])
api_router.include_router(indexing.router, prefix="/v1", tags=["indexing"])
api_router.include_router(faces.router, prefix="/faces", tags=["faces"])
api_router.include_router(sessions.router, prefix="/sessions", tags=["sessions"])
api_router.include_router(events.router, prefix="/events", tags=["events"])
