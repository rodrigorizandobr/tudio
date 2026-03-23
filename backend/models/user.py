from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional
from datetime import datetime

class RuleModel(BaseModel):
    name: str # e.g. "script:create"
    description: Optional[str] = None

class GroupModel(BaseModel):
    name: str # e.g. "admin", "editor"
    rules: List[str] = [] # List of Rule names
    is_deleted: bool = False
    
class UserModel(BaseModel):
    email: EmailStr
    hashed_password: str
    full_name: Optional[str] = None
    is_active: bool = True
    groups: List[str] = [] # List of Group names
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

# Auth Schemas (Input/Output)
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None

class UserResponse(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None
    is_active: bool
    groups: List[str] = []
    
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    username: Optional[str] = None
