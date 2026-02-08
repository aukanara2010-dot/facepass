from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
import redis
from app.api.deps import get_db
from core.config import get_settings

router = APIRouter()
settings = get_settings()


@router.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """
    Health check endpoint
    Checks connectivity to main database and Redis
    """
    health_status = {
        "status": "healthy",
        "database": "unknown",
        "redis": "unknown"
    }
    
    # Check database connection
    try:
        db.execute(text("SELECT 1"))
        health_status["database"] = "connected"
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["database"] = f"error: {str(e)}"
    
    # Check Redis connection
    try:
        redis_client = redis.Redis.from_url(settings.redis_url)
        redis_client.ping()
        health_status["redis"] = "connected"
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["redis"] = f"error: {str(e)}"
    
    if health_status["status"] == "unhealthy":
        raise HTTPException(status_code=503, detail=health_status)
    
    return health_status
