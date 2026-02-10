"""Complete FastAPI application with authentication and monitoring.

Run with:
    uvicorn api.app_complete:app --reload --host 0.0.0.0 --port 8000
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import auth, admin, detection, monitoring
from api.middleware import MetricsMiddleware, RequestLoggingMiddleware
from persistence.database import init_db, get_db
from persistence.user_repository import UserRepository
from api.auth.jwt_handler import get_password_hash


def create_default_admin():
    """Create default admin user if not exists."""
    try:
        db = next(get_db())
        user_repo = UserRepository(db)
        
        # Check if admin exists
        admin = user_repo.get_by_username("admin")
        if not admin:
            print("Creating default admin user...")
            user_repo.create({
                "username": "admin",
                "email": "admin@llmobservability.local",
                "hashed_password": get_password_hash("admin123"),
                "role": "admin",
                "rate_limit_tier": "enterprise",
            })
            print("✅ Default admin created: username='admin', password='admin123'")
        
        # Create test users if not exist
        test_user = user_repo.get_by_username("testuser")
        if not test_user:
            user_repo.create({
                "username": "testuser",
                "email": "test@llmobservability.local",
                "hashed_password": get_password_hash("test123"),
                "role": "user",
                "rate_limit_tier": "free",
            })
            print("✅ Test user created: username='testuser', password='test123'")
    
    except Exception as e:
        print(f"⚠️ Error creating default users: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle management for FastAPI app."""
    # Startup
    print("🚀 Starting LLM Observability API v5.0...")
    try:
        init_db()
        print("✅ Database initialized")
        create_default_admin()
    except Exception as e:
        print(f"⚠️ Startup warning: {e}")
    
    print("📊 API ready at http://localhost:8000")
    print("📚 Docs at http://localhost:8000/docs")
    print("🎯 Dashboard: streamlit run dashboard/admin_dashboard.py")
    
    yield
    
    # Shutdown
    print("🛑 Shutting down LLM Observability API...")


app = FastAPI(
    title="LLM Observability API",
    description="Production-grade LLM observability with 3-tier detection, JWT auth, and rate limiting",
    version="5.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add custom middleware
app.add_middleware(MetricsMiddleware)
app.add_middleware(RequestLoggingMiddleware)

# Include routers
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(detection.router)
app.include_router(monitoring.router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "LLM Observability API",
        "version": "5.0.0",
        "status": "operational",
        "features": [
            "3-tier detection (Regex, Semantic, LLM Agent)",
            "JWT authentication",
            "Rate limiting",
            "Admin dashboard",
            "Real-time monitoring",
        ],
        "endpoints": {
            "docs": "/docs",
            "health": "/api/monitoring/health",
            "detect": "/api/detect",
            "login": "/api/auth/login",
        },
        "default_credentials": {
            "admin": {"username": "admin", "password": "admin123"},
            "user": {"username": "testuser", "password": "test123"},
        },
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
