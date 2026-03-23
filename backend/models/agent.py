from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict

class AgentModel(BaseModel):
    id: Optional[str] = None  # String ID (slug-like or auto-generated)
    name: str
    description: str = ""
    icon: str = "Bot"  # Lucide icon name


    
    # Prompt Templates
    prompt_init: str = ""
    prompt_chapters: str = ""
    prompt_subchapters: str = ""
    prompt_subchapters: str = ""
    prompt_scenes: str = ""
    prompt_image_search: str = "" # Sprint 64: Fallback Image Search Prompt
    
    # Metadata
    is_default: bool = False  # Track if this is the default agent
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Default Agent",
                "prompt_init": "Create script...",
                "icon": "Bot",
                "is_default": True

            }
        }
    )
