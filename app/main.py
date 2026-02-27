from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import PlainTextResponse
from app.api.v1.router import api_router
import asyncio
import logging
import structlog
import time

# Import models to ensure they are registered with Base
from models.face import FaceEmbedding
from core.database import Base, engine

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

# Get structured logger
logger = structlog.get_logger()

# Create tables if they don't exist
try:
    # Create vector database tables
    Base.metadata.create_all(bind=engine, tables=[FaceEmbedding.__table__])
    logger.info("database_tables_created", status="success")
    
except Exception as e:
    logger.warning("database_table_creation_warning", error=str(e))

# Create FastAPI app
app = FastAPI(
    title="FacePass",
    version="2.0.0",
    description="Isolated face recognition microservice with vector search"
)

# Store startup time for uptime calculation
app.state.startup_time = time.time()

# Setup rate limiting
from app.middleware.rate_limit import setup_rate_limiting
setup_rate_limiting(app)

# Startup event to initialize face recognition service
@app.on_event("startup")
async def startup_event():
    """
    Initialize services on application startup.
    
    This ensures the FaceAnalysis model is loaded once at startup
    and reused throughout the application lifecycle.
    """
    logger.info("server_startup", status="initializing")
    
    try:
        # Initialize face recognition service (singleton)
        from services.face_recognition import get_face_recognition_service
        
        logger.info("loading_insightface_model")
        face_service = get_face_recognition_service()
        
        if face_service.initialized:
            logger.info("insightface_model_loaded", status="success")
        else:
            logger.warning("insightface_not_initialized", status="warning")
    
    except Exception as e:
        logger.error("face_recognition_initialization_error", error=str(e), exc_info=True)
    
    logger.info("server_startup_complete", status="running")

# CORS middleware - configurable via environment variables
from core.config import get_settings
settings = get_settings()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "Accept", "X-API-Key"],
)

# Custom middleware for handling long-running operations and permissions
@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    
    # Security headers
    response.headers["Permissions-Policy"] = "camera=(self)"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    
    # Content Security Policy
    csp = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com https://cdnjs.cloudflare.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdnjs.cloudflare.com; "
        "font-src 'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com; "
        "img-src 'self' data: https: blob:; "
        "media-src 'self' blob:; "
        "connect-src 'self' https:; "
        "frame-src 'none'; "
        "object-src 'none'; "
        "base-uri 'self';"
    )
    response.headers["Content-Security-Policy"] = csp
    
    return response

@app.middleware("http")
async def request_logging_middleware(request, call_next):
    """
    Log all API requests with structured logging.
    
    Logs request details, response status, and execution time.
    """
    start_time = time.time()
    
    # Log request
    logger.info(
        "request_started",
        method=request.method,
        path=request.url.path,
        client_ip=request.client.host if request.client else None
    )
    
    try:
        response = await call_next(request)
        
        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000
        
        # Log response
        logger.info(
            "request_completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=round(duration_ms, 2)
        )
        
        return response
        
    except Exception as e:
        # Log error
        duration_ms = (time.time() - start_time) * 1000
        logger.error(
            "request_failed",
            method=request.method,
            path=request.url.path,
            error=str(e),
            duration_ms=round(duration_ms, 2),
            exc_info=True
        )
        raise
# Note: Static files removed in v2.0 (API-only microservice)

# Include API router
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root():
    """
    API root endpoint.
    
    Returns basic information about the FacePass API.
    """
    return {
        "service": "FacePass v2.0",
        "description": "Isolated face recognition microservice",
        "version": "2.0.0",
        "docs": "/docs",
        "health": "/api/v1/health",
        "metrics": "/api/v1/metrics"
    }


@app.get("/api")
async def api_info():
    """API information endpoint"""
    return {
        "message": "FacePass API v2.0", 
        "version": "2.0.0",
        "docs": "/docs",
        "redoc": "/redoc",
        "health": "/api/v1/health",
        "metrics": "/api/v1/metrics"
    }
