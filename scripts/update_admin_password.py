"""
Update the admin user's password in Datastore.
Usage:
    PYTHONPATH=. python scripts/update_admin_password.py
    PYTHONPATH=. python scripts/update_admin_password.py --email user@example.com --password newpassword
"""
import sys
import os
import asyncio
import argparse

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.repositories.user_repository import user_repository
from backend.services.auth_service import auth_service
from backend.core.logger import log


async def update_password(email: str, new_password: str):
    log.info(f"Looking up user: {email}")
    user = await user_repository.get_user_by_email(email)

    if not user:
        log.error(f"User '{email}' not found in Datastore.")
        sys.exit(1)

    log.info("Hashing new password...")
    user.hashed_password = await auth_service.get_password_hash(new_password)

    await user_repository.save_user(user)
    log.info(f"Password updated successfully for user: {email}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Update admin user password in Datastore")
    parser.add_argument("--email", default="rodrigorizando@gmail.com", help="User email")
    parser.add_argument(
        "--password",
        default=os.environ.get("ADMIN_PASSWORD", "admin@123"),
        help="New password (defaults to ADMIN_PASSWORD env var or 'admin@123')",
    )
    args = parser.parse_args()

    asyncio.run(update_password(args.email, args.password))
