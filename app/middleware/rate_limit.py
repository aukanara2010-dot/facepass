"""
Rate limiting middleware for FacePass.

This module provides rate limiting functionality to protect against abuse
and ensure fair resource usage.
"""

import logging
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request
from core.config import get_settings

logger = logging.getLogger(__name__)

# Initialize limiter
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["1000/minute"],
    storage_uri="memory://",  # Use in-memory storage (for Redis, use redis://host:port)
    strategy="fixed-window"
)


def get_api_key_from_request(request: Request) -> str:
    """
    Extract API key from request for rate limiting by API key.
    
    Args:
        request: FastAPI request
        
    Returns:
        API key or IP address if no key provided
    """
    api_key = request.headers.get("X-API-Key")
    if api_key:
        return f"api_key:{api_key}"
    return get_remote_address(request)


# Rate limit decorators for different endpoint types
INDEXING_RATE_LIMIT = "100/minute"  # 100 requests per minute for indexing
SEARCH_RATE_LIMIT = "1000/minute"   # 1000 requests per minute for search


def setup_rate_limiting(app):
    """
    Setup rate limiting for FastAPI app.
    
    Args:
        app: FastAPI application instance
    """
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    
    logger.info("Rate limiting configured")
