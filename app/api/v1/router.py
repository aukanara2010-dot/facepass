from fastapi import APIRouter
from app.api.v1.endpoints import health, faces, events, sessions

api_router = APIRouter()

# Include endpoint routers
api_router.include_router(health.router, tags=["health"])
api_router.include_router(events.router, prefix="/events", tags=["events"])
api_router.include_router(faces.router, prefix="/faces", tags=["faces"])
api_router.include_router(sessions.router, prefix="/sessions", tags=["sessions"])
