"""
Photo Session validation endpoints.

This module provides API endpoints for validating photo sessions
and checking FacePass status from the external Pixora database.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Dict, Any, List
import os
import logging

from core.database import get_pixora_db
from models.photo_session import PhotoSession
from app.schemas.photo_session import SessionValidationResponse, PhotoSessionResponse
from core.config import get_settings

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get(
    "/validate/{session_id}",
    response_model=SessionValidationResponse,
    summary="Validate photo session",
    description="Validate if a photo session exists and has FacePass enabled"
)
async def validate_session(
    session_id: str,
    pixora_db: Session = Depends(get_pixora_db)
) -> SessionValidationResponse:
    """
    Validate photo session and FacePass status.
    
    This endpoint checks the external Pixora database to verify:
    1. Session exists
    2. FacePass is enabled for the session
    
    Args:
        session_id (str): The photo session UUID to validate
        pixora_db (Session): Database session for Pixora database
        
    Returns:
        SessionValidationResponse: Validation result with session data or error
        
    Raises:
        HTTPException: If there's a database connection error
    """
    try:
        # Query the external Pixora database for the session
        session = pixora_db.query(PhotoSession).filter(
            PhotoSession.id == session_id
        ).first()
        
        # Check if session exists and FacePass is enabled
        if not session:
            return SessionValidationResponse(
                valid=False,
                session=None,
                error="Session not found"
            )
        
        if not session.is_facepass_active():
            return SessionValidationResponse(
                valid=False,
                session=PhotoSessionResponse.from_orm(session),
                error="FacePass is not enabled for this session"
            )
        
        # Session is valid
        return SessionValidationResponse(
            valid=True,
            session=PhotoSessionResponse.from_orm(session),
            error=None
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database connection error: {str(e)}"
        )


@router.get(
    "/{session_id}",
    response_model=PhotoSessionResponse,
    summary="Get photo session details",
    description="Get photo session details from external Pixora database"
)
async def get_session(
    session_id: str,
    pixora_db: Session = Depends(get_pixora_db)
) -> PhotoSessionResponse:
    """
    Get photo session details.
    
    Args:
        session_id (str): The photo session UUID
        pixora_db (Session): Database session for Pixora database
        
    Returns:
        PhotoSessionResponse: Session details
        
    Raises:
        HTTPException: If session not found or database error
    """
    try:
        session = pixora_db.query(PhotoSession).filter(
            PhotoSession.id == session_id
        ).first()
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        return PhotoSessionResponse.from_orm(session)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database connection error: {str(e)}"
        )


@router.get(
    "/{session_id}/facepass-status",
    response_model=Dict[str, Any],
    summary="Check FacePass status",
    description="Check if FacePass is enabled for a specific session"
)
async def check_facepass_status(
    session_id: str,
    pixora_db: Session = Depends(get_pixora_db)
) -> Dict[str, Any]:
    """
    Check FacePass status for a session.
    
    Args:
        session_id (str): The photo session UUID
        pixora_db (Session): Database session for Pixora database
        
    Returns:
        Dict[str, Any]: FacePass status information
        
    Raises:
        HTTPException: If session not found or database error
    """
    try:
        session = pixora_db.query(PhotoSession).filter(
            PhotoSession.id == session_id
        ).first()
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        return {
            "session_id": session_id,
            "facepass_enabled": session.facepass_enabled,
            "is_active": session.is_facepass_active(),
            "session_name": session.name,
            "studio_id": session.studio_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database connection error: {str(e)}"
        )


@router.get(
    "/{session_id}/interface",
    response_class=HTMLResponse,
    summary="FacePass interface page",
    description="Serve the FacePass interface HTML page for a specific session"
)
async def session_interface(
    session_id: str,
    request: Request,
    pixora_db: Session = Depends(get_pixora_db)
) -> HTMLResponse:
    """
    Serve FacePass interface page for a session.
    
    This endpoint first validates the session and then serves the HTML interface
    if the session is valid and FacePass is enabled.
    
    Args:
        session_id (str): The photo session UUID
        request (Request): FastAPI request object
        pixora_db (Session): Database session for Pixora database
        
    Returns:
        HTMLResponse: HTML page for FacePass interface or error page
    """
    try:
        settings = get_settings()
        
        # Validate session first
        session = pixora_db.query(PhotoSession).filter(
            PhotoSession.id == session_id
        ).first()
        
        if not session:
            return HTMLResponse(
                content=f"""
                <!DOCTYPE html>
                <html>
                <head><title>Сессия не найдена</title></head>
                <body style="font-family: Arial; text-align: center; padding: 50px;">
                    <h1>❌ Сессия не найдена</h1>
                    <p>Сессия с ID {session_id} не существует.</p>
                </body>
                </html>
                """,
                status_code=404
            )
        
        if not session.is_facepass_active():
            return HTMLResponse(
                content=f"""
                <!DOCTYPE html>
                <html>
                <head><title>FacePass не активен</title></head>
                <body style="font-family: Arial; text-align: center; padding: 50px;">
                    <h1>⚠️ FacePass не активен</h1>
                    <p>FacePass не включен для сессии "{session.name}".</p>
                    <p>Обратитесь к администратору для активации.</p>
                </body>
                </html>
                """,
                status_code=403
            )
        
        # Read and serve the HTML file
        html_path = os.path.join("app", "static", "session", "index.html")
        
        if not os.path.exists(html_path):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Interface file not found"
            )
        
        with open(html_path, "r", encoding="utf-8") as f:
            html_content = f.read()
        
        # Inject session ID into the HTML
        html_content = html_content.replace(
            "this.getSessionIdFromUrl()",
            f"'{session_id}'"
        )
        
        # Inject MAIN_API_URL from settings
        # Handle all possible template variations (with and without spaces)
        main_api_url = settings.MAIN_API_URL
        
        # Replace all possible template variations
        replacements = [
            # With spaces
            ("'{{ MAIN_API_URL }}'", f"'{main_api_url}'"),
            ('"{{ MAIN_API_URL }}"', f'"{main_api_url}"'),
            ('{{ MAIN_API_URL }}', main_api_url),
            # Without spaces
            ("'{{MAIN_API_URL}}'", f"'{main_api_url}'"),
            ('"{{MAIN_API_URL}}"', f'"{main_api_url}"'),
            ('{{MAIN_API_URL}}', main_api_url),
        ]
        
        replaced = False
        for old, new in replacements:
            if old in html_content:
                html_content = html_content.replace(old, new)
                replaced = True
                logger.info(f"Replaced '{old}' with '{new}'")
        
        if not replaced:
            logger.warning(f"MAIN_API_URL template not found in HTML. Checking content...")
            # Log a snippet to debug
            if 'window.MAIN_API_URL' in html_content:
                start = html_content.find('window.MAIN_API_URL')
                snippet = html_content[start:start+150]
                logger.warning(f"Found window.MAIN_API_URL: {snippet}")
        
        logger.info(f"Serving interface for session {session_id} with MAIN_API_URL: {main_api_url}")
        
        return HTMLResponse(content=html_content)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error serving interface: {str(e)}"
        )


@router.get(
    "/{session_id}/services",
    response_model=Dict[str, Any],
    summary="Get session services and pricing",
    description="Get available services and pricing for a photo session from Pixora API"
)
async def get_session_services(
    session_id: str,
    pixora_db: Session = Depends(get_pixora_db)
) -> Dict[str, Any]:
    """
    Get services and pricing for a session.
    
    This endpoint fetches available services for a photo session
    from the Pixora database through the service_packages relationship.
    
    Schema: photo_sessions -> service_package_id -> service_package_services -> services
    
    Args:
        session_id (str): The photo session UUID
        pixora_db (Session): Database session for Pixora database
        
    Returns:
        Dict[str, Any]: Services and pricing information
        
    Raises:
        HTTPException: If session not found or database error
    """
    try:
        settings = get_settings()
        
        # First validate session exists
        session = pixora_db.query(PhotoSession).filter(
            PhotoSession.id == session_id
        ).first()
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        # Query services for this session through service_packages
        # Schema: photo_sessions -> service_package_id -> service_package_services -> services
        query = text("""
            SELECT 
                s.id,
                s.name,
                s.description,
                s.price,
                sps.is_default,
                s.type,
                s.photo_count,
                s.is_active
            FROM public.photo_sessions ps
            INNER JOIN public.service_packages sp ON ps.service_package_id = sp.id
            INNER JOIN public.service_package_services sps ON sp.id = sps.service_package_id
            INNER JOIN public.services s ON sps.service_id = s.id
            WHERE ps.id = :session_id
                AND s.is_active = true
            ORDER BY sps.is_default DESC, s.price ASC
        """)
        
        result = pixora_db.execute(query, {"session_id": session_id})
        
        services = []
        default_service = None
        
        for row in result:
            service = {
                "id": row[0],
                "name": row[1],
                "description": row[2],
                "price": float(row[3]) if row[3] else 0.0,
                "isDefault": bool(row[4]),
                "type": row[5],
                "photoCount": row[6],
                "isActive": bool(row[7])
            }
            
            services.append(service)
            
            if service["isDefault"]:
                default_service = service
        
        logger.info(f"Found {len(services)} services for session {session_id}")
        
        return {
            "sessionId": session_id,
            "sessionName": session.name,
            "services": services,
            "defaultService": default_service,
            "currency": "RUB",
            "mainUrl": settings.MAIN_URL
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching services for session {session_id}: {str(e)}")
        # Return empty services if table doesn't exist or other error
        # This allows the interface to work in view-only mode
        return {
            "sessionId": session_id,
            "sessionName": session.name if session else "Unknown",
            "services": [],
            "defaultService": None,
            "currency": "RUB",
            "mainUrl": settings.MAIN_URL,
            "error": "Services not available"
        }