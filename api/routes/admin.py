"""Admin API endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from typing import List

from api.auth.models import User, UserRole, RateLimitTier
from api.auth.dependencies import require_admin
from persistence.user_repository import UserRepository
from enforcement.control_tower_v3 import ControlTowerV3

router = APIRouter()
user_repo = UserRepository()
control_tower = ControlTowerV3()


@router.get("/users", response_model=List[User])
async def list_users(admin: User = Depends(require_admin)):
    """List all users (admin only)."""
    return user_repo.list_users()


@router.put("/users/{username}/role")
async def update_user_role(
    username: str,
    role: UserRole,
    admin: User = Depends(require_admin)
):
    """Update user role (admin only)."""
    user = user_repo.update_user_role(username, role)
    
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {"username": username, "role": role.value, "message": "Role updated"}


@router.put("/users/{username}/tier")
async def update_rate_limit_tier(
    username: str,
    tier: RateLimitTier,
    admin: User = Depends(require_admin)
):
    """Update user rate limit tier (admin only)."""
    user = user_repo.update_rate_limit_tier(username, tier)
    
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {"username": username, "tier": tier.value, "message": "Tier updated"}


@router.delete("/users/{username}")
async def disable_user(
    username: str,
    admin: User = Depends(require_admin)
):
    """Disable user account (admin only)."""
    user = user_repo.disable_user(username)
    
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {"username": username, "message": "User disabled"}


@router.get("/stats")
async def get_system_stats(admin: User = Depends(require_admin)):
    """Get system statistics (admin only)."""
    tier_stats = control_tower.get_tier_stats()
    
    return {
        "tier_distribution": tier_stats["distribution"],
        "health": tier_stats["health"],
        "total_checks": tier_stats["total_checks"],
        "users": len(user_repo.list_users())
    }