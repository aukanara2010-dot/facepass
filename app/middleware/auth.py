"""
API Key authentication middleware for FacePass.

This module provides API key-based authentication for protected endpoints.
"""

import logging
from typing import Optional
from fastapi import Request, HTTPException, status
from fastapi.security import APIKeyHeader

from core.config import get_settings

logger = logging.getLogger(__name__)

# API Key header scheme
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def verify_api_key(api_key: Optional[str]) -> bool:
    """
    Verify if the provided API key is valid.
    
    Args:
        api_key: API key to verify
        
    Returns:
        bool: True if valid, False otherwise
    """
    if not api_key:
        return False
    
    settings = get_settings()
    valid_keys = settings.get_api_keys()
    
    # If no API keys configured, allow all requests (development mode)
    if not valid_keys:
        logger.warning("No API keys configured - authentication disabled!")
        return True
    
    return api_key in valid_keys


async def require_api_key(request: Request) -> None:
    """
    Dependency that requires a valid API key.
    
    This function can be used as a FastAPI dependency to protect endpoints.
    It checks for the X-API-Key header and validates it against configured keys.
    
    Args:
        request: FastAPI request object
        
    Raises:
        HTTPException 401: If API key is missing or invalid
        
    Example:
        @router.post("/protected", dependencies=[Depends(require_api_key)])
        async def protected_endpoint():
            return {"message": "Access granted"}
    """
    # Get API key from header
    api_key = request.headers.get("X-API-Key")
    
    if not api_key:
        logger.warning(f"API key missing for {request.method} {request.url.path}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required. Provide X-API-Key header.",
            headers={"WWW-Authenticate": "ApiKey"}
        )
    
    # Verify API key
    if not verify_api_key(api_key):
        logger.warning(f"Invalid API key attempt for {request.method} {request.url.path}: {api_key[:8]}...")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "ApiKey"}
        )
    
    logger.info(f"API key authenticated for {request.method} {request.url.path}")


class APIKeyMiddleware:
    """
    Middleware for API key authentication.
    
    This middleware can be added to the FastAPI app to automatically
    check API keys for specific routes.
    """
    
    def __init__(self, app, protected_prefixes: list[str] = None):
        """
        Initialize API key middleware.
        
        Args:
            app: FastAPI application
            protected_prefixes: List of URL prefixes that require API key
        """
        self.app = app
        self.protected_prefixes = protected_prefixes or ["/api/v1/index"]
    
    async def __call__(self, request: Request, call_next):
        """
        Process request and check API key if needed.
        
        Args:
            request: FastAPI request
            call_next: Next middleware/handler
            
        Returns:
            Response from next handler
        """
        # Check if this path requires API key
        path = request.url.path
        requires_auth = any(path.startswith(prefix) for prefix in self.protected_prefixes)
        
        if requires_auth:
            # Get API key from header
            api_key = request.headers.get("X-API-Key")
            
            if not api_key:
                logger.warning(f"API key missing for {request.method} {path}")
                return HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="API key required. Provide X-API-Key header.",
                    headers={"WWW-Authenticate": "ApiKey"}
                )
            
            # Verify API key
            if not verify_api_key(api_key):
                logger.warning(f"Invalid API key for {request.method} {path}")
                return HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid API key",
                    headers={"WWW-Authenticate": "ApiKey"}
                )
            
            logger.info(f"API key authenticated for {request.method} {path}")
        
        # Continue to next handler
        response = await call_next(request)
        return response
