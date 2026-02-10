"""Pydantic models for authentication."""

from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional


class Token(BaseModel):
    """JWT token response."""
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Token payload data."""
    username: Optional[str] = None
    role: Optional[str] = None


class UserBase(BaseModel):
    """Base user model."""
    username: str
    email: str  # Changed from EmailStr to allow .local domains
    
    @field_validator('email')
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Validate email format (relaxed for development)."""
        if '@' not in v:
            raise ValueError('Invalid email format')
        if len(v) < 3:
            raise ValueError('Email too short')
        return v.lower()


class UserCreate(UserBase):
    """User creation model."""
    password: str


class UserResponse(UserBase):
    """User response model."""
    role: str
    rate_limit_tier: str
    disabled: bool = False
    
    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    """User update model."""
    email: Optional[str] = None
    role: Optional[str] = None
    rate_limit_tier: Optional[str] = None
    disabled: Optional[bool] = None
    
    @field_validator('email')
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        """Validate email format (relaxed for development)."""
        if v is None:
            return v
        if '@' not in v:
            raise ValueError('Invalid email format')
        if len(v) < 3:
            raise ValueError('Email too short')
        return v.lower()
