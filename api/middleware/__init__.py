"""API middleware modules."""

# Import rate limiter functions
from .rate_limiter import (
    check_rate_limit,
    get_rate_limit,
    reset_rate_limit,
    get_rate_limit_info,
    RATE_LIMITS,
)

# Import middleware classes from parent module
import sys
import os

# Get the parent api directory
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

try:
    # Import from api.middleware (the .py file)
    from middleware import MetricsMiddleware, RequestLoggingMiddleware
except ImportError:
    # Fallback: create dummy classes if import fails
    from starlette.middleware.base import BaseHTTPMiddleware
    
    class MetricsMiddleware(BaseHTTPMiddleware):
        """Dummy metrics middleware."""
        async def dispatch(self, request, call_next):
            return await call_next(request)
    
    class RequestLoggingMiddleware(BaseHTTPMiddleware):
        """Dummy logging middleware."""
        async def dispatch(self, request, call_next):
            return await call_next(request)

__all__ = [
    "check_rate_limit",
    "get_rate_limit",
    "reset_rate_limit",
    "get_rate_limit_info",
    "RATE_LIMITS",
    "MetricsMiddleware",
    "RequestLoggingMiddleware",
]
