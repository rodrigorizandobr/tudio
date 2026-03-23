from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
from datetime import datetime
from backend.models.video import VideoStatus, ChapterModel, SceneModel, CharacterModel

# Reusing Models as base or defining schemas if distinct separation needed.
# For simplicity, implementing Request/Response schemas.

class VideoCreate(BaseModel):
    prompt: str
    target_duration_minutes: int
    language: str = "pt-br"
    auto_image_source: Optional[str] = "none" # none, unsplash, google, bing
    auto_generate_narration: Optional[bool] = False
    transition_type: Optional[str] = "fade"
    aspect_ratios: List[str] = ["16:9"] # 16:9, 9:16
    agent_id: Optional[str] = None
    script_content: Optional[str] = None
    stop_after_scenes: Optional[bool] = False
    audio_transition_padding: Optional[float] = Field(default=0.5, ge=0.3)

class VideoRead(BaseModel):
    id: int
    prompt: str
    target_duration_minutes: int
    language: str
    status: VideoStatus
    progress: float
    rendering_progress: float = 0.0
    total_duration_seconds: float = 0.0
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    visual_style: Optional[str] = ""
    aspect_ratios: List[str] = ["16:9"]
    outputs: dict[str, str] = {}
    title: Optional[str] = ""
    description: Optional[str] = ""
    tags: Optional[str] = ""
    timestamps_index: Optional[str] = None
    video_url: Optional[str] = None # Still used for backward compatibility or primary link
    auto_image_source: Optional[str] = "none"
    audio_transition_padding: float = 0.5
    audio_generation_instructions: Optional[str] = None
    music_id: Optional[int] = None
    agent_id: Optional[str] = None
    characters: List[CharacterModel] = []
    
    # Captions (Sprint 200)
    caption_status: str = "none"
    caption_progress: float = 0.0
    caption_style: str = "karaoke"
    caption_options: dict = {}
    captioned_outputs: dict = {}

    chapters: List[ChapterModel] = []

    model_config = ConfigDict(from_attributes=True)
