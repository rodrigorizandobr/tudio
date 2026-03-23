import sys
import os
import asyncio
from datetime import datetime

# Add project root to path
sys.path.append(os.getcwd())

from backend.repositories.user_repository import user_repository
from backend.services.auth_service import auth_service
from backend.models.user import UserModel
from backend.core.logger import log

async def seed_user():
    email = "rodrigorizando@gmail.com"
    password = "admin@123"
    
    log.info(f"Checking for user {email}...")
    user = user_repository.get_user_by_email(email)
    
    if user:
        log.info(f"User {email} already exists. Updating password just in case...")
        user.hashed_password = auth_service.get_password_hash(password)
        user.updated_at = datetime.now()
        user_repository.save_user(user)
        log.info("User updated.")
    else:
        log.info(f"User {email} not found. Creating...")
        hashed_password = auth_service.get_password_hash(password)
        new_user = UserModel(
            email=email,
            hashed_password=hashed_password,
            full_name="Rodrigo Test User",
            is_active=True,
            groups=["Super Admin"],
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        user_repository.save_user(new_user)
        log.info("User created successfully.")

if __name__ == "__main__":
    asyncio.run(seed_user())
