from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.api.v1.router import api_router

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
        "http://localhost:3000",  # For local development
        "http://localhost:8000",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "Accept"],
)

# Mount static files for gallery
app.mount("/gallery", StaticFiles(directory="app/static/gallery", html=True), name="gallery")

# Include API router
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root():
    return {"message": "Fecapass API", "version": "1.0.0"}
