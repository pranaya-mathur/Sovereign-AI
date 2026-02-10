"""Authentication routes for JWT-based auth."""

from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from api.auth.jwt_handler import (
    create_access_token,
    verify_token,
    get_password_hash,
    verify_password,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)
from api.auth.models import Token, UserCreate, UserResponse
from persistence.database import get_db
from persistence.user_repository import UserRepository


router = APIRouter(prefix="/api/auth", tags=["auth"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")


async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)], db: Session = Depends(get_db)):
    """Get current authenticated user."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    username = verify_token(token)
    if username is None:
        raise credentials_exception
    
    user_repo = UserRepository(db)
    user = user_repo.get_by_username(username)
    
    if user is None or user.disabled:
        raise credentials_exception
    
    return user


async def get_current_admin_user(current_user = Depends(get_current_user)):
    """Get current user and verify admin role."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


@router.post("/register", response_model=UserResponse)
async def register(
    user_data: UserCreate,
    db: Session = Depends(get_db),
):
    """Register a new user."""
    user_repo = UserRepository(db)
    
    # Check if user exists
    existing_user = user_repo.get_by_username(user_data.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered",
        )
    
    existing_email = user_repo.get_by_email(user_data.email)
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    
    # Create user
    hashed_password = get_password_hash(user_data.password)
    user = user_repo.create({
        "username": user_data.username,
        "email": user_data.email,
        "hashed_password": hashed_password,
        "role": "user",  # Default role
        "rate_limit_tier": "free",  # Default tier
    })
    
    return UserResponse(
        username=user.username,
        email=user.email,
        role=user.role,
        rate_limit_tier=user.rate_limit_tier,
        disabled=user.disabled,
    )


@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Session = Depends(get_db),
):
    """OAuth2 compatible token login, get an access token for future requests."""
    user_repo = UserRepository(db)
    user = user_repo.get_by_username(form_data.username)
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if user.disabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled",
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role},
        expires_delta=access_token_expires,
    )
    
    return Token(access_token=access_token, token_type="bearer")


@router.post("/login", response_model=Token)
async def login(
    username: str,
    password: str,
    db: Session = Depends(get_db),
):
    """Simple login endpoint for dashboard."""
    user_repo = UserRepository(db)
    user = user_repo.get_by_username(username)
    
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    
    if user.disabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled",
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role},
        expires_delta=access_token_expires,
    )
    
    return Token(access_token=access_token, token_type="bearer")


@router.get("/me", response_model=UserResponse)
async def get_me(current_user = Depends(get_current_user)):
    """Get current user details."""
    return UserResponse(
        username=current_user.username,
        email=current_user.email,
        role=current_user.role,
        rate_limit_tier=current_user.rate_limit_tier,
        disabled=current_user.disabled,
    )
