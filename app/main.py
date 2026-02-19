from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.api.v1.router import api_router
import asyncio

# Import models to ensure they are registered with Base
from models.event import Event
from models.face import Face, FaceEmbedding
from core.database import Base, main_engine, vector_engine

# Create tables if they don't exist
try:
    # Create main database tables
    Base.metadata.create_all(bind=main_engine, tables=[Event.__table__, Face.__table__])
    print("✅ Main database tables created/verified")
    
    # Create vector database tables
    Base.metadata.create_all(bind=vector_engine, tables=[FaceEmbedding.__table__])
    print("✅ Vector database tables created/verified")
    
except Exception as e:
    print(f"⚠️ Database table creation warning: {str(e)}")

# Increase timeout for long-running operations like photo indexing
# This is especially important for the first-time indexing of large photo sessions
asyncio.get_event_loop().set_debug(False)

app = FastAPI(
    title="Fecapass",
    version="1.0.0",
    description="Face recognition service with Docker architecture"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://facepass.pixorasoft.ru",
        "https://staging.pixorasoft.ru",
        "https://pixorasoft.ru",
        "http://localhost:3000",  # For local development
        "http://localhost:8000",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "Accept"],
)

# Custom middleware for handling long-running operations
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

# Include API router
app.include_router(api_router, prefix="/api/v1")


# Public session route for beautiful URLs
@app.get("/session/{session_id}")
async def public_session_interface(session_id: str):
    """
    Public route for FacePass session interface.
    
    This provides a beautiful URL: https://facepass.pixorasoft.ru/session/{session_id}
    instead of the API path /api/v1/sessions/{session_id}/interface
    """
    from fastapi import Request, Depends
    from fastapi.responses import HTMLResponse
    from sqlalchemy.orm import Session
    from core.database import get_pixora_db
    from models.photo_session import PhotoSession
    import os
    
    # Validate session first
    pixora_db = next(get_pixora_db())
    try:
        session = pixora_db.query(PhotoSession).filter(
            PhotoSession.id == session_id
        ).first()
        
        if not session:
            return HTMLResponse(
                content=f"""
                <!DOCTYPE html>
                <html lang="ru">
                <head>
                    <meta charset="UTF-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <title>Сессия не найдена - FacePass</title>
                    <script src="https://cdn.tailwindcss.com"></script>
                </head>
                <body class="min-h-screen bg-gradient-to-br from-purple-600 to-blue-600 flex items-center justify-center">
                    <div class="bg-white rounded-2xl p-8 text-center max-w-md mx-4">
                        <div class="text-6xl mb-4">❌</div>
                        <h1 class="text-2xl font-bold text-gray-800 mb-4">Сессия не найдена</h1>
                        <p class="text-gray-600 mb-6">Сессия с ID {session_id} не существует или была удалена.</p>
                        <a href="https://pixorasoft.ru" class="bg-purple-600 text-white px-6 py-3 rounded-lg hover:bg-purple-700 transition-colors">
                            Вернуться на главную
                        </a>
                    </div>
                </body>
                </html>
                """,
                status_code=404
            )
        
        if not session.is_facepass_active():
            return HTMLResponse(
                content=f"""
                <!DOCTYPE html>
                <html lang="ru">
                <head>
                    <meta charset="UTF-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <title>FacePass не активен - {session.name}</title>
                    <script src="https://cdn.tailwindcss.com"></script>
                </head>
                <body class="min-h-screen bg-gradient-to-br from-purple-600 to-blue-600 flex items-center justify-center">
                    <div class="bg-white rounded-2xl p-8 text-center max-w-md mx-4">
                        <div class="text-6xl mb-4">⚠️</div>
                        <h1 class="text-2xl font-bold text-gray-800 mb-4">FacePass не активен</h1>
                        <p class="text-gray-600 mb-2">FacePass не включен для сессии:</p>
                        <p class="font-semibold text-gray-800 mb-6">"{session.name}"</p>
                        <p class="text-sm text-gray-500 mb-6">Обратитесь к фотографу для активации FacePass.</p>
                        <a href="https://pixorasoft.ru" class="bg-purple-600 text-white px-6 py-3 rounded-lg hover:bg-purple-700 transition-colors">
                            Вернуться на главную
                        </a>
                    </div>
                </body>
                </html>
                """,
                status_code=403
            )
        
        # Read and serve the HTML file with session data injection
        html_path = os.path.join("app", "static", "session", "index.html")
        
        if not os.path.exists(html_path):
            return HTMLResponse(
                content="<h1>Interface file not found</h1>",
                status_code=500
            )
        
        with open(html_path, "r", encoding="utf-8") as f:
            html_content = f.read()
        
        # Inject session data into HTML
        html_content = html_content.replace(
            '<title>FacePass - Поиск фотографий</title>',
            f'<title>Найти фото - {session.name} | FacePass</title>'
        )
        
        # Inject session ID into JavaScript (remove the old method)
        # Update title and meta tags
        html_content = html_content.replace(
            '<title>FacePass - Поиск фотографий</title>',
            f'<title>Найти фото - {session.name} | FacePass</title>'
        )
        
        # Inject OpenGraph and meta tags
        html_content = html_content.replace(
            '<meta name="description" content="Сделайте селфи, и наш AI покажет все ваши фотографии с фотосессии. Быстро, точно, удобно.">',
            f'''<meta name="description" content="Найдите свои фотографии с фотосессии '{session.name}' с помощью технологии распознавания лиц FacePass от Pixora">
    
    <!-- OpenGraph Meta Tags -->
    <meta property="og:title" content="Найти фото - {session.name} | FacePass">
    <meta property="og:description" content="Найдите свои фотографии с фотосессии '{session.name}' с помощью технологии распознавания лиц FacePass">
    <meta property="og:image" content="https://facepass.pixorasoft.ru/static/images/facepass-logo.svg">
    <meta property="og:url" content="https://facepass.pixorasoft.ru/session/{session_id}">
    <meta property="og:type" content="website">
    <meta property="og:site_name" content="FacePass by Pixora">
    
    <!-- Twitter Card Meta Tags -->
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="Найти фото - {session.name} | FacePass">
    <meta name="twitter:description" content="Найдите свои фотографии с фотосессии '{session.name}' с помощью технологии распознавания лиц FacePass">
    <meta name="twitter:image" content="https://facepass.pixorasoft.ru/static/images/facepass-logo.svg">
    
    <!-- Additional Meta Tags -->
    <meta name="keywords" content="фотосессия, поиск фото, распознавание лиц, FacePass, Pixora, {session.name}">
    <meta name="author" content="Pixora">
    
    <!-- Favicon -->
    <link rel="icon" type="image/svg+xml" href="/static/images/facepass-logo.svg">
    <link rel="apple-touch-icon" href="/static/images/facepass-logo.svg">'''
        )
        
        return HTMLResponse(content=html_content)
        
    finally:
        pixora_db.close()


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
