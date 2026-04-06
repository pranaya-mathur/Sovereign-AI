"""JWT token handling utilities."""

from datetime import datetime, timedelta
from typing import Optional
import os
import bcrypt

from jose import JWTError, jwt


# JWT Configuration
_DEFAULT_SECRET = "your-secret-key-change-in-production-use-openssl-rand-hex-32"
SECRET_KEY = os.getenv("JWT_SECRET_KEY", _DEFAULT_SECRET)

# Production check: Fail-fast if using default secret in production
ENVIRONMENT = os.getenv("ENV") or os.getenv("ENVIRONMENT") or "development"
if ENVIRONMENT.lower() == "production" and SECRET_KEY == _DEFAULT_SECRET:
    raise RuntimeError(
        "CRITICAL SECURITY ERROR: JWT_SECRET_KEY must be explicitly set in production environments. "
        "Use 'openssl rand -hex 32' to generate a secure key."
    )

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours



def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash.
    
    Args:
        plain_password: Plain text password
        hashed_password: Bcrypt hashed password (string)
        
    Returns:
        True if password matches, False otherwise
    """
    try:
        return bcrypt.checkpw(
            plain_password.encode('utf-8'),
            hashed_password.encode('utf-8') if isinstance(hashed_password, str) else hashed_password
        )
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt.
    
    Args:
        password: Plain text password
        
    Returns:
        Bcrypt hashed password as string
        
    Note: 
        Bcrypt has a 72-byte limit. Longer passwords are automatically
        truncated by bcrypt itself, but we do it explicitly for clarity.
    """
    # Truncate to 72 bytes (bcrypt's limit)
    password_bytes = password.encode('utf-8')[:72]
    
    # Generate salt and hash
    salt = bcrypt.gensalt(rounds=12)  # 12 rounds is a good balance
    hashed = bcrypt.hashpw(password_bytes, salt)
    
    # Return as string
    return hashed.decode('utf-8')


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token.
    
    Args:
        data: Dictionary of data to encode in token
        expires_delta: Optional expiration time delta
        
    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    
    return encoded_jwt


def verify_token(token: str) -> Optional[str]:
    """Verify a JWT token and return the username.
    
    Args:
        token: JWT token string
        
    Returns:
        Username from token if valid, None otherwise
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        
        if username is None:
            return None
        
        return username
    
    except JWTError:
        return None


def decode_token(token: str) -> Optional[dict]:
    """Decode a JWT token and return the full payload.
    
    Args:
        token: JWT token string
        
    Returns:
        Dictionary of token payload if valid, None otherwise
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    
    except JWTError:
        return None
