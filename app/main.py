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
@app.middleware("http")
async def timeout_middleware(request, call_next):
    """
    Custom middleware to handle timeouts for long-running operations.
    
    Increases timeout for photo indexing endpoints that may take several minutes
    to process large photo sessions.
    """
    import asyncio
    from fastapi import HTTPException
    
    # Define endpoints that need extended timeouts (in seconds)
    extended_timeout_endpoints = {
        "/api/v1/faces/search-session": 600,  # 10 minutes for search with auto-indexing
        "/api/v1/faces/index-session": 900,   # 15 minutes for manual indexing
    }
    
    # Get timeout for this endpoint
    timeout = extended_timeout_endpoints.get(request.url.path, 30)  # Default 30 seconds
    
    try:
        # Execute the request with timeout
        response = await asyncio.wait_for(call_next(request), timeout=timeout)
        return response
    except asyncio.TimeoutError:
        # Return timeout error with helpful message
        if request.url.path in extended_timeout_endpoints:
            raise HTTPException(
                status_code=408,
                detail={
                    "error": "Request timeout",
                    "message": f"Operation took longer than {timeout} seconds. This may happen with large photo sessions.",
                    "suggestion": "Try again or contact support if the issue persists.",
                    "timeout_seconds": timeout
                }
            )
        else:
            raise HTTPException(status_code=408, detail="Request timeout")
    except Exception as e:
        # Re-raise other exceptions
        raise e

# Mount static files for gallery and session interface
app.mount("/gallery", StaticFiles(directory="app/static/gallery", html=True), name="gallery")
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Add robots.txt endpoint for SEO and security
@app.get("/robots.txt", response_class=PlainTextResponse)
async def robots_txt():
    """Serve robots.txt for search engine crawlers and security"""
    try:
        with open("app/static/robots.txt", "r") as f:
            return f.read()
    except FileNotFoundError:
        return """User-agent: *
Allow: /
Allow: /static/
Allow: /session/
Disallow: /api/
Disallow: /docs
Disallow: /redoc
Crawl-delay: 1"""

# Add security.txt endpoint for responsible disclosure
@app.get("/.well-known/security.txt", response_class=PlainTextResponse)
async def security_txt():
    """Serve security.txt for responsible vulnerability disclosure"""
    try:
        with open("app/static/.well-known/security.txt", "r") as f:
            return f.read()
    except FileNotFoundError:
        return """Contact: security@pixorasoft.ru
Expires: 2025-12-31T23:59:59.000Z
Canonical: https://facepass.pixorasoft.ru/.well-known/security.txt"""

# Add sitemap.xml endpoint for SEO
@app.get("/sitemap.xml", response_class=PlainTextResponse)
async def sitemap_xml():
    """Serve sitemap.xml for search engines"""
    try:
        with open("app/static/sitemap.xml", "r") as f:
            return f.read()
    except FileNotFoundError:
        return """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    <url>
        <loc>https://facepass.pixorasoft.ru/</loc>
        <changefreq>weekly</changefreq>
        <priority>1.0</priority>
    </url>
</urlset>"""

# Include API router
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def landing_page():
    """
    Serve the main landing page.
    
    This is the entry point for users who want to search for their photos.
    """
    from fastapi.responses import HTMLResponse
    import os
    
    # Read and serve the landing page HTML
    html_path = os.path.join("app", "static", "index.html")
    
    if not os.path.exists(html_path):
        return HTMLResponse(
            content="<h1>Landing page not found</h1>",
            status_code=500
        )
    
    with open(html_path, "r", encoding="utf-8") as f:
        html_content = f.read()
    
    return HTMLResponse(content=html_content)


@app.get("/api")
async def api_root():
    return {
        "message": "FacePass API", 
        "version": "1.0.0",
        "docs": "/docs",
        "public_interface": "/session/{session_id}",
        "landing_page": "/"
    }
