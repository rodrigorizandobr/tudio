from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from backend.core.configs import settings
from backend.models.user import UserModel, TokenData
from backend.repositories.user_repository import user_repository
from backend.services.auth_service import auth_service

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")

async def get_current_user(token: str = Depends(oauth2_scheme)) -> UserModel:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    
    user = await user_repository.get_user_by_email(username)
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return user

def get_current_active_superuser(
    current_user: UserModel = Depends(get_current_user),
) -> UserModel:
    # Check if user has 'admin' or 'Super Admin' group
    if "admin" not in current_user.groups and "Super Admin" not in current_user.groups:
         raise HTTPException(
            status_code=403, detail="The user doesn't have enough privileges"
        )
    return current_user
