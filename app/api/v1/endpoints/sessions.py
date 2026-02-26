"""
Session interface endpoints.

This module provides the public FacePass interface for photo sessions.
In the isolated microservice architecture, session validation is handled
by the client application (Pixora), not by FacePass.
"""

from fastapi import APIRouter, HTTPException, status, Request
from fastapi.responses import HTMLResponse
import os
import logging

from core.config import get_settings

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get(
    "/{session_id}",
    response_class=HTMLResponse,
    summary="FacePass interface page",
    description="Serve the FacePass interface HTML page for a specific session"
)
async def session_interface(
    session_id: str,
    request: Request
) -> HTMLResponse:
    """
    Serve FacePass interface page for a session.
    
    This endpoint serves the HTML interface for face recognition search.
    Session validation is handled by the client application (Pixora).
    
    Args:
        session_id (str): The photo session UUID
        request (Request): FastAPI request object
        
    Returns:
        HTMLResponse: HTML page for FacePass interface
        
    Raises:
        HTTPException: If interface file not found
    """
    try:
        settings = get_settings()
        
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
        
        logger.info(f"Serving interface for session {session_id}")
        
        return HTMLResponse(content=html_content)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error serving interface: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error serving interface: {str(e)}"
        )
