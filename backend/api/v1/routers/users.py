from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from backend.api.deps import get_current_user, get_current_active_superuser
from backend.models.user import UserModel, GroupModel
from backend.repositories.user_repository import user_repository

router = APIRouter()

# --- Users ---

@router.get("/me", response_model=UserModel)
async def read_users_me(
    current_user: UserModel = Depends(get_current_user)
):
    """
    Get current user profile.
    """
    return current_user

# --- Groups ---

@router.get("/groups", response_model=List[GroupModel])
async def list_groups(
    current_user: UserModel = Depends(get_current_user)
):
    """
    List all user groups.
    Requires admin privileges (checked via rules in real app, here checking rule or simply authenticated for MVP).
    """
    # TODO: Add specific rule check like 'group:read'
    return await user_repository.list_groups()

@router.post("/groups", response_model=GroupModel)
async def create_group(
    group: GroupModel,
    current_user: UserModel = Depends(get_current_active_superuser)
):
    """
    Create or update a group.
    """
    return await user_repository.save_group(group)

@router.delete("/groups/{name}")
async def delete_group(
    name: str,
    current_user: UserModel = Depends(get_current_active_superuser)
):
    """
    Delete a group.
    """
    await user_repository.delete_group(name)
    return {"status": "success"}
