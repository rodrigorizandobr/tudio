from fastapi import APIRouter, Depends, HTTPException
from typing import Dict
from pydantic import BaseModel
from backend.api.deps import get_current_user, get_current_active_superuser
from backend.models.user import UserModel
from backend.services.settings_service import settings_service

router = APIRouter()

class SettingItem(BaseModel):
    key: str
    value: str

class SettingsUpdate(BaseModel):
    settings: Dict[str, str]

@router.get("", response_model=Dict[str, str])
async def get_settings(
    current_user: UserModel = Depends(get_current_active_superuser)
):
    """
    Get all environment variables as dict.
    Requires Admin.
    """
    import asyncio
    settings_list = await asyncio.to_thread(settings_service.get_all)
    return {item["key"]: item["value"] for item in settings_list}

@router.post("", response_model=Dict[str, str])
async def update_settings(
    update_data: SettingsUpdate,
    current_user: UserModel = Depends(get_current_active_superuser)
):
    """
    Update environment variables.
    Requires Admin.
    """
    import asyncio
    await asyncio.to_thread(settings_service.update, update_data.settings)
    return {"status": "updated", "message": "Settings saved. Restart server to apply changes."}

@router.get("/validate-prompts", response_model=Dict[str, bool])
async def validate_prompts(
    current_user: UserModel = Depends(get_current_user)
):
    """
    Check if all required prompts are configured.
    Returns boolean status for each prompt.
    """
    from backend.core.configs import settings as pydantic_settings
    
    return {
        "PROMPT_INIT_TEMPLATE": bool(pydantic_settings.PROMPT_INIT_TEMPLATE and pydantic_settings.PROMPT_INIT_TEMPLATE.strip()),
        "PROMPT_CHAPTERS_TEMPLATE": bool(pydantic_settings.PROMPT_CHAPTERS_TEMPLATE and pydantic_settings.PROMPT_CHAPTERS_TEMPLATE.strip()),
        "PROMPT_SUBCHAPTERS_TEMPLATE": bool(pydantic_settings.PROMPT_SUBCHAPTERS_TEMPLATE and pydantic_settings.PROMPT_SUBCHAPTERS_TEMPLATE.strip()),
        "PROMPT_SCENES_TEMPLATE": bool(pydantic_settings.PROMPT_SCENES_TEMPLATE and pydantic_settings.PROMPT_SCENES_TEMPLATE.strip())
    }
