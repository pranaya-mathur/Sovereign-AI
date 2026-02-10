"""Admin routes for user and system management."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from api.routes.auth import get_current_admin_user
from api.auth.models import UserResponse
from persistence.database import get_db
from persistence.user_repository import UserRepository


router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/users", response_model=List[UserResponse])
async def get_all_users(
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_admin_user),
):
    """Get all users (admin only)."""
    user_repo = UserRepository(db)
    users = user_repo.get_all()
    
    return [
        UserResponse(
            username=user.username,
            email=user.email,
            role=user.role,
            rate_limit_tier=user.rate_limit_tier,
            disabled=user.disabled,
        )
        for user in users
    ]


@router.get("/users/{username}", response_model=UserResponse)
async def get_user(
    username: str,
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_admin_user),
):
    """Get user by username (admin only)."""
    user_repo = UserRepository(db)
    user = user_repo.get_by_username(username)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    return UserResponse(
        username=user.username,
        email=user.email,
        role=user.role,
        rate_limit_tier=user.rate_limit_tier,
        disabled=user.disabled,
    )


@router.put("/users/{username}/role", response_model=UserResponse)
async def update_user_role(
    username: str,
    role: str,
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_admin_user),
):
    """Update user role (admin only)."""
    if role not in ["admin", "user", "viewer"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid role. Must be: admin, user, or viewer",
        )
    
    user_repo = UserRepository(db)
    user = user_repo.update_role(username, role)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    return UserResponse(
        username=user.username,
        email=user.email,
        role=user.role,
        rate_limit_tier=user.rate_limit_tier,
        disabled=user.disabled,
    )


@router.put("/users/{username}/tier", response_model=UserResponse)
async def update_user_tier(
    username: str,
    tier: str,
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_admin_user),
):
    """Update user rate limit tier (admin only)."""
    if tier not in ["free", "pro", "enterprise"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid tier. Must be: free, pro, or enterprise",
        )
    
    user_repo = UserRepository(db)
    user = user_repo.update_tier(username, tier)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    return UserResponse(
        username=user.username,
        email=user.email,
        role=user.role,
        rate_limit_tier=user.rate_limit_tier,
        disabled=user.disabled,
    )


@router.put("/users/{username}/disable", response_model=UserResponse)
async def disable_user(
    username: str,
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_admin_user),
):
    """Disable user account (admin only)."""
    if username == current_admin.username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot disable your own account",
        )
    
    user_repo = UserRepository(db)
    user = user_repo.disable_user(username)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    return UserResponse(
        username=user.username,
        email=user.email,
        role=user.role,
        rate_limit_tier=user.rate_limit_tier,
        disabled=user.disabled,
    )


@router.put("/users/{username}/enable", response_model=UserResponse)
async def enable_user(
    username: str,
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_admin_user),
):
    """Enable user account (admin only)."""
    user_repo = UserRepository(db)
    user = user_repo.enable_user(username)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    return UserResponse(
        username=user.username,
        email=user.email,
        role=user.role,
        rate_limit_tier=user.rate_limit_tier,
        disabled=user.disabled,
    )


@router.delete("/users/{username}")
async def delete_user(
    username: str,
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_admin_user),
):
    """Delete user (admin only)."""
    if username == current_admin.username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account",
        )
    
    user_repo = UserRepository(db)
    success = user_repo.delete(username)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    return {"message": f"User {username} deleted successfully"}
