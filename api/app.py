"""Main FastAPI application."""

from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from datetime import timedelta
import time

from api.auth.jwt_handler import create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES
from api.auth.models import Token, UserCreate, User
from api.auth.dependencies import get_current_active_user, require_admin
from api.middleware.rate_limiter import RateLimiter
from persistence.user_repository import UserRepository

from api.routes import detection, admin, monitoring

# Initialize FastAPI app
app = FastAPI(
    title="LLM Observability API",
    description="Production-grade LLM observability with 3-tier detection",
    version="5.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize dependencies
user_repo = UserRepository()
rate_limiter = RateLimiter()


# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add processing time to response headers."""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": "5.0.0",
        "phase": "5"
    }


# Authentication endpoints
@app.post("/api/auth/register", response_model=User)
async def register(user_create: UserCreate):
    """Register a new user."""
    try:
        user = user_repo.create_user(user_create)
        return User(**user.dict())
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@app.post("/api/auth/login", response_model=Token)
async def login(username: str, password: str):
    """Login and get access token."""
    user = user_repo.authenticate_user(username, password)
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role.value},
        expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/api/auth/me", response_model=User)
async def get_me(current_user: User = Depends(get_current_active_user)):
    """Get current user info."""
    return current_user


# Include routers
app.include_router(detection.router, prefix="/api", tags=["detection"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])
app.include_router(monitoring.router, prefix="/api/monitoring", tags=["monitoring"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)