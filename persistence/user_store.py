"""User store for managing user data.

Provides CRUD operations for user management with SQLite/PostgreSQL.
"""

from typing import Optional, List
from datetime import datetime
import json

from sqlalchemy.orm import Session
from sqlalchemy import text
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class UserStore:
    """User storage and management."""

    def __init__(self, db: Session):
        """Initialize user store.
        
        Args:
            db: Database session
        """
        self.db = db
        self._ensure_table()
        self._ensure_default_users()

    def _ensure_table(self):
        """Ensure users table exists."""
        try:
            self.db.execute(text("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT,
                    password_hash TEXT NOT NULL,
                    role TEXT DEFAULT 'user',
                    rate_limit_tier TEXT DEFAULT 'free',
                    disabled BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            self.db.commit()
        except Exception as e:
            print(f"Warning: Could not create users table: {e}")
            self.db.rollback()

    def _ensure_default_users(self):
        """Create default admin user if not exists."""
        try:
            # Check if admin exists
            result = self.db.execute(
                text("SELECT username FROM users WHERE username = :username"),
                {"username": "admin"}
            )
            if result.fetchone() is None:
                # Create default admin
                admin_password_hash = pwd_context.hash("admin123")
                self.db.execute(
                    text("""
                        INSERT INTO users (username, email, password_hash, role, rate_limit_tier)
                        VALUES (:username, :email, :password_hash, :role, :tier)
                    """),
                    {
                        "username": "admin",
                        "email": "admin@llm-obs.local",
                        "password_hash": admin_password_hash,
                        "role": "admin",
                        "tier": "enterprise",
                    }
                )
                
                # Create test user
                user_password_hash = pwd_context.hash("user123")
                self.db.execute(
                    text("""
                        INSERT INTO users (username, email, password_hash, role, rate_limit_tier)
                        VALUES (:username, :email, :password_hash, :role, :tier)
                    """),
                    {
                        "username": "testuser",
                        "email": "user@llm-obs.local",
                        "password_hash": user_password_hash,
                        "role": "user",
                        "tier": "pro",
                    }
                )
                
                self.db.commit()
                print("✅ Default users created (admin/admin123, testuser/user123)")
        except Exception as e:
            print(f"Warning: Could not create default users: {e}")
            self.db.rollback()

    def create_user(
        self,
        username: str,
        password: str,
        email: Optional[str] = None,
        role: str = "user",
        rate_limit_tier: str = "free",
    ) -> dict:
        """Create a new user.
        
        Args:
            username: Unique username
            password: Plain text password (will be hashed)
            email: User email
            role: User role (admin, user, viewer)
            rate_limit_tier: Rate limit tier (free, pro, enterprise)
        
        Returns:
            Created user dict
        """
        password_hash = pwd_context.hash(password)
        
        try:
            self.db.execute(
                text("""
                    INSERT INTO users (username, email, password_hash, role, rate_limit_tier)
                    VALUES (:username, :email, :password_hash, :role, :tier)
                """),
                {
                    "username": username,
                    "email": email,
                    "password_hash": password_hash,
                    "role": role,
                    "tier": rate_limit_tier,
                }
            )
            self.db.commit()
            return self.get_by_username(username)
        except Exception as e:
            self.db.rollback()
            raise ValueError(f"Could not create user: {e}")

    def get_by_username(self, username: str) -> Optional[dict]:
        """Get user by username.
        
        Args:
            username: Username to lookup
        
        Returns:
            User dict or None
        """
        try:
            result = self.db.execute(
                text("""
                    SELECT id, username, email, password_hash, role, 
                           rate_limit_tier, disabled, created_at, updated_at
                    FROM users
                    WHERE username = :username
                """),
                {"username": username}
            )
            row = result.fetchone()
            if row:
                return {
                    "id": row[0],
                    "username": row[1],
                    "email": row[2],
                    "password_hash": row[3],
                    "role": row[4],
                    "rate_limit_tier": row[5],
                    "disabled": bool(row[6]),
                    "created_at": row[7],
                    "updated_at": row[8],
                }
            return None
        except Exception as e:
            print(f"Error getting user: {e}")
            return None

    def get_all_users(self) -> List[dict]:
        """Get all users.
        
        Returns:
            List of user dicts
        """
        try:
            result = self.db.execute(
                text("""
                    SELECT id, username, email, role, rate_limit_tier, disabled, created_at
                    FROM users
                    ORDER BY created_at DESC
                """)
            )
            users = []
            for row in result:
                users.append({
                    "id": row[0],
                    "username": row[1],
                    "email": row[2],
                    "role": row[3],
                    "rate_limit_tier": row[4],
                    "disabled": bool(row[5]),
                    "created_at": row[6],
                })
            return users
        except Exception as e:
            print(f"Error getting users: {e}")
            return []

    def update_role(self, username: str, role: str) -> bool:
        """Update user role.
        
        Args:
            username: Username to update
            role: New role
        
        Returns:
            True if successful
        """
        try:
            self.db.execute(
                text("""
                    UPDATE users
                    SET role = :role, updated_at = CURRENT_TIMESTAMP
                    WHERE username = :username
                """),
                {"username": username, "role": role}
            )
            self.db.commit()
            return True
        except Exception as e:
            self.db.rollback()
            print(f"Error updating role: {e}")
            return False

    def update_tier(self, username: str, tier: str) -> bool:
        """Update user rate limit tier.
        
        Args:
            username: Username to update
            tier: New tier
        
        Returns:
            True if successful
        """
        try:
            self.db.execute(
                text("""
                    UPDATE users
                    SET rate_limit_tier = :tier, updated_at = CURRENT_TIMESTAMP
                    WHERE username = :username
                """),
                {"username": username, "tier": tier}
            )
            self.db.commit()
            return True
        except Exception as e:
            self.db.rollback()
            print(f"Error updating tier: {e}")
            return False

    def disable_user(self, username: str, disabled: bool = True) -> bool:
        """Enable/disable user.
        
        Args:
            username: Username to update
            disabled: Disable flag
        
        Returns:
            True if successful
        """
        try:
            self.db.execute(
                text("""
                    UPDATE users
                    SET disabled = :disabled, updated_at = CURRENT_TIMESTAMP
                    WHERE username = :username
                """),
                {"username": username, "disabled": disabled}
            )
            self.db.commit()
            return True
        except Exception as e:
            self.db.rollback()
            print(f"Error disabling user: {e}")
            return False

    def delete_user(self, username: str) -> bool:
        """Delete user.
        
        Args:
            username: Username to delete
        
        Returns:
            True if successful
        """
        try:
            self.db.execute(
                text("DELETE FROM users WHERE username = :username"),
                {"username": username}
            )
            self.db.commit()
            return True
        except Exception as e:
            self.db.rollback()
            print(f"Error deleting user: {e}")
            return False
