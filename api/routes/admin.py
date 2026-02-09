"""Admin API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from api.models import UserResponse, UserCreateRequest
from api.routes.auth import require_admin, get_current_user
from persistence.database import get_db
from persistence.user_store import UserStore

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/users", response_model=List[UserResponse])
async def list_users(
    admin: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """List all users (admin only)."""
    user_store = UserStore(db)
    users = user_store.get_all_users()
    
    return [
        UserResponse(
            username=user["username"],
            email=user.get("email", ""),
            role=user["role"],
            rate_limit_tier=user.get("rate_limit_tier", "free"),
            disabled=user.get("disabled", False),
        )
        for user in users
    ]


@router.post("/users", response_model=UserResponse)
async def create_user(
    user_request: UserCreateRequest,
    admin: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Create new user (admin only)."""
    user_store = UserStore(db)
    
    # Check if user already exists
    existing_user = user_store.get_by_username(user_request.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists",
        )
    
    try:
        created_user = user_store.create_user(
            username=user_request.username,
            password=user_request.password,
            email=user_request.email,
            role=user_request.role,
            rate_limit_tier=user_request.rate_limit_tier,
        )
        
        return UserResponse(
            username=created_user["username"],
            email=created_user.get("email", ""),
            role=created_user["role"],
            rate_limit_tier=created_user.get("rate_limit_tier", "free"),
            disabled=created_user.get("disabled", False),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create user: {str(e)}",
        )


@router.put("/users/{username}/role")
async def update_user_role(
    username: str,
    role: str,
    admin: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Update user role (admin only)."""
    if role not in ["admin", "user", "viewer"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid role. Must be: admin, user, or viewer",
        )
    
    user_store = UserStore(db)
    
    # Check if user exists
    user = user_store.get_by_username(username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    success = user_store.update_role(username, role)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update role",
        )
    
    return {"username": username, "role": role, "message": "Role updated successfully"}


@router.put("/users/{username}/tier")
async def update_rate_limit_tier(
    username: str,
    tier: str,
    admin: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Update user rate limit tier (admin only)."""
    if tier not in ["free", "pro", "enterprise"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid tier. Must be: free, pro, or enterprise",
        )
    
    user_store = UserStore(db)
    
    # Check if user exists
    user = user_store.get_by_username(username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    success = user_store.update_tier(username, tier)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update tier",
        )
    
    return {"username": username, "tier": tier, "message": "Tier updated successfully"}


@router.put("/users/{username}/disable")
async def disable_user(
    username: str,
    disabled: bool = True,
    admin: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Enable/disable user account (admin only)."""
    user_store = UserStore(db)
    
    # Check if user exists
    user = user_store.get_by_username(username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    # Prevent disabling yourself
    if username == admin["username"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot disable your own account",
        )
    
    success = user_store.disable_user(username, disabled)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to disable user",
        )
    
    action = "disabled" if disabled else "enabled"
    return {"username": username, "disabled": disabled, "message": f"User {action} successfully"}


@router.delete("/users/{username}")
async def delete_user(
    username: str,
    admin: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Delete user account (admin only)."""
    user_store = UserStore(db)
    
    # Check if user exists
    user = user_store.get_by_username(username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    # Prevent deleting yourself
    if username == admin["username"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account",
        )
    
    success = user_store.delete_user(username)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete user",
        )
    
    return {"username": username, "message": "User deleted successfully"}
