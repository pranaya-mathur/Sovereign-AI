import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.getcwd()))

from persistence.database import SessionLocal, init_db
from persistence.user_repository import UserRepository
from api.auth.jwt_handler import get_password_hash

def seed_admin():
    print("Seeding admin user...")
    db = SessionLocal()
    try:
        user_repo = UserRepository(db)
        
        # Check if admin already exists
        if user_repo.get_by_username("admin"):
            print("Admin user already exists.")
            return

        hashed_password = get_password_hash("admin123")
        user = user_repo.create({
            "username": "admin",
            "email": "admin@sovereign-ai.com",
            "hashed_password": hashed_password,
            "role": "admin",
            "rate_limit_tier": "enterprise",
            "disabled": False
        })
        print(f"✅ Admin user created: {user.username}")
    finally:
        db.close()

if __name__ == "__main__":
    init_db()
    seed_admin()
