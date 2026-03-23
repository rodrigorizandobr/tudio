import asyncio
from datetime import datetime, timedelta
from typing import Optional
from jose import jwt, JWTError
from passlib.context import CryptContext
from backend.core.configs import settings
from backend.models.user import TokenData

pwd_context = CryptContext(
    schemes=["bcrypt"], 
    deprecated="auto",
    bcrypt__rounds=12  # Explicit rounds for security (GAP-SEC-04 Fix)
)

class AuthService:
    async def verify_password(self, plain_password, hashed_password):
        return await asyncio.to_thread(pwd_context.verify, plain_password, hashed_password)

    async def get_password_hash(self, password):
        return await asyncio.to_thread(pwd_context.hash, password)

    async def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None):
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.ALGORITHM)
        return encoded_jwt

auth_service = AuthService()
