"""Zero-trust authentication middleware for API key + JWT."""

from __future__ import annotations

import logging
import os
from typing import Iterable

from fastapi import HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
try:
    from slowapi import Limiter
    from slowapi.util import get_remote_address
except Exception:  # pragma: no cover - optional dependency fallback
    class Limiter:  # type: ignore[override]
        def __init__(self, *args, **kwargs):
            self.key_func = kwargs.get("key_func")

    def get_remote_address(request: Request) -> str:  # type: ignore[override]
        return request.client.host if request.client else "unknown"
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

logger = logging.getLogger(__name__)

limiter = Limiter(key_func=get_remote_address)
_bearer = HTTPBearer(auto_error=False)
_DEFAULT_OPEN_PATHS: tuple[str, ...] = (
    "/",
    "/health",
    "/docs",
    "/openapi.json",
    "/redoc",
    "/metrics",
    "/api/auth",
)


def _public_paths() -> set[str]:
    configured = os.getenv("AUTH_EXEMPT_PATHS", "")
    paths = {
        p.strip()
        for p in configured.split(",")
        if p.strip()
    }
    paths.update(_DEFAULT_OPEN_PATHS)
    return paths


def _matches_any(path: str, candidates: Iterable[str]) -> bool:
    for candidate in candidates:
        if path == candidate or path.startswith(candidate.rstrip("/") + "/"):
            return True
    return False


def _verify_jwt(token: str) -> bool:
    secret = os.getenv("JWT_SECRET_KEY")
    if not secret:
        logger.error("JWT_SECRET_KEY is not set; JWT validation cannot proceed.")
        return False

    try:
        jwt.decode(token, secret, algorithms=["HS256"])
        return True
    except JWTError:
        return False


def _api_key_valid(request: Request) -> bool:
    configured_api_key = os.getenv("SOVEREIGN_API_KEY", "")
    if not configured_api_key:
        return False
    incoming = request.headers.get("x-api-key", "")
    return bool(incoming) and incoming == configured_api_key


def _jwt_valid(creds: HTTPAuthorizationCredentials | None) -> bool:
    if creds is None:
        return False
    if creds.scheme.lower() != "bearer":
        return False
    return _verify_jwt(creds.credentials)


class APIKeyJWTAuthMiddleware(BaseHTTPMiddleware):
    """Require either valid API key or valid Bearer JWT on protected endpoints."""

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path
        if _matches_any(path, _public_paths()):
            return await call_next(request)

        creds = await _bearer(request)
        if _api_key_valid(request) or _jwt_valid(creds):
            return await call_next(request)

        detail = "Missing or invalid credentials. Provide x-api-key or Bearer JWT."
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": detail},
        )


def require_api_key_or_jwt(request: Request) -> None:
    """Dependency helper for protected route handlers."""
    if _api_key_valid(request):
        return
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="API key or JWT required.",
    )
