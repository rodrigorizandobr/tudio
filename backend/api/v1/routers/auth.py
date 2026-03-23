from datetime import timedelta
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from backend.core.configs import settings
from backend.services.auth_service import auth_service
from backend.repositories.user_repository import user_repository
from backend.models.user import Token
import logging

log = logging.getLogger(__name__)

# Import limiter from dedicated module (avoids circular import)
from backend.core.rate_limiting import limiter

router = APIRouter()

@router.post("/login", response_model=Token)
@limiter.limit("5/15minutes")  # Rate limiting: max 5 attempts per 15 minutes (GAP-SEC-02 Fix)
async def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends()) -> Any:
    """
    Login endpoint with rate limiting to prevent brute force attacks.
    Allows maximum 5 login attempts per 15 minutes per IP address.
    """
    log.info(f"Login attempt - username: {form_data.username}, password_length: {len(form_data.password) if form_data.password else 0}")
    user = await user_repository.get_user_by_email(form_data.username)
    if not user or not await auth_service.verify_password(form_data.password, user.hashed_password):
         log.warning(f"Login failed for {form_data.username} - user_exists: {user is not None}")
         raise HTTPException(status_code=400, detail="Incorrect email or password")
    
    if not user.is_active:
         raise HTTPException(status_code=400, detail="Inactive user")

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = await auth_service.create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {
        "access_token": access_token,
        "token_type": "bearer",
    }
