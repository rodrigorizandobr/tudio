from typing import List, Optional, Any
from enum import Enum
from datetime import datetime
from backend.core.configs import settings
from pydantic import BaseModel, Field, model_validator, ConfigDict

class VideoStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    RENDERING = "rendering"
    RENDERING_SCENES = "rendering_scenes"
    COMPLETED = "completed"
    ERROR = "error"
    CANCELLED = "cancelled"

class CharacterModel(BaseModel):
    name: str
    physical_description: str
    description: Optional[str] = None 
    voice: str

    @model_validator(mode='before')
    @classmethod
    def check_voice_alias(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if 'voice' not in data and 'voice_type' in data:
                data['voice'] = data['voice_type']
        return data

class SceneModel(BaseModel):
    id: int
    order: int
    duration_seconds: int = 0
    narration_content: str
    character: Optional[str] = None # Renamed from character_name, used for voice lookup
    
    # Deprecated fields (kept optional for simple migration safety if needed, or removed if strict)
    # User said "cannot return this attribute", so we remove 'voice' from the active expectation.
    # We can keep 'character_name' as alias for 'character' if old data exists, but let's stick to new schema.
    
    # New Standard Schema Fields
    audio_effect_search: Optional[str] = None
    audio_effect_seconds_start: Optional[int] = 0
    
    visual_description: Optional[str] = "" 
    image_prompt: str
    video_prompt: str
    audio_prompt: Optional[str] = None 
    
    image_search: Optional[str] = None
    image_search_provider: Optional[str] = None
    video_search: Optional[str] = None
    audio_search: Optional[str] = None
    
    audio_url: Optional[str] = None
    # Image storage (Sprint 43)
    original_image_url: Optional[str] = None
    cropped_image_url: Optional[str] = None
    
    # Video storage (Sprint 66)
    video_url: Optional[str] = None
    generated_video_url: Optional[str] = None # Legacy: Default ratio clip
    captioned_video_url: Optional[str] = None # Legacy: Default ratio captioned clip
    
    # Sprint 350: Support for multiple ratios (16:9, 9:16, etc.)
    generated_video_urls: dict[str, str] = Field(default_factory=dict)
    captioned_video_urls: dict[str, str] = Field(default_factory=dict)
    deleted: bool = False # Sprint 123: Soft Delete

    # Captions (Sprint 200)
    caption_words: List[dict] = Field(default_factory=list)  # [{word, start, end}]
    caption_status: str = "none"  # none | processing | done | error

class SubChapterModel(BaseModel):
    id: int
    order: int
    title: str
    description: str
    scenes: List[SceneModel] = []

class ChapterModel(BaseModel):
    id: int
    order: int
    title: str
    estimated_duration_minutes: float
    description: str
    subchapters: List[SubChapterModel] = []
    
    # Status tracking (Sprint 50)
    status: VideoStatus = VideoStatus.PENDING # Default to PENDING for safety (Sprint 200)
    error_message: Optional[str] = None

class VideoModel(BaseModel):
    id: Optional[int] = None # Datastore ID
    prompt: str
    language: str = "pt-BR" # Default language
    target_duration_minutes: int
    openai_thread_id: Optional[str] = None # Added for OpenAI Assistants API Context
    
    # Metadata (Sprint 62)
    status: VideoStatus
    progress: float = 0.0
    rendering_progress: float = 0.0
    total_duration_seconds: float = 0.0  # Changed from int to float to match ffprobe output
    error_message: Optional[str] = None
    timestamps_index: Optional[str] = None # Generated YouTube timestamps
    
    @model_validator(mode='before')
    @classmethod
    def coerce_none_strings(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # Fields that must be strings but might be None in legacy/intermediate data
            str_fields = ['visual_style', 'title', 'description', 'tags', 'music']
            for field in str_fields:
                if field in data and data[field] is None:
                    data[field] = ""
            
            # Migration: aspect_ratio (singular) to aspect_ratios (list)
            if 'aspect_ratio' in data and 'aspect_ratios' not in data:
                val = data.pop('aspect_ratio')
                data['aspect_ratios'] = [val] if val else ["16:9"]
        return data

    # Timestamps
    created_at: Optional[datetime] = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = Field(default_factory=datetime.now)
    deleted_at: Optional[datetime] = None # Soft delete (Sprint 69)


    # New Fields
    visual_style: str = Field(default="")
    aspect_ratios: List[str] = Field(default_factory=lambda: ["16:9"]) # List of formats: 16:9, 9:16
    agent_id: Optional[str] = None
    characters: List[CharacterModel] = Field(default_factory=list)
    script_content: Optional[str] = None

    # Metadata (Sprint 62)
    title: str = Field(default="")
    description: str = Field(default="")
    tags: str = Field(default="")
    music: str = Field(default="") # Sprint 63 (Legacy string)

    music_id: Optional[int] = None # Sprint 105 (Reference)

    # Sprint 68: Multi-Format Outputs
    outputs: dict[str, str] = Field(default_factory=dict) # Mapping "16:9" -> "videos/ID/final_horizontal.mp4"

    # Sprint 64: Auto-Images
    auto_image_source: str = "none" # none, unsplash, google, bing
    
    # Sprint 67: User Controls
    auto_generate_narration: bool = False
    transition_type: str = "fade" # fade, wipeleft, slideright, random
    audio_transition_padding: float = settings.DEFAULT_AUDIO_PADDING_SECONDS # Seconds of silence at start/end of scene (Sprint 71)
    
    # Sprint 72: Audio Instructions
    audio_generation_instructions: str = "Atue como um locutor profissional brasileiro, nativo de São Paulo. Seu sotaque deve ser exclusivamente brasileiro (paulistano). Nunca use entonação ou pronúncia de Portugal. Fale de forma calma e pausada."
    
    # Sprint 68: Outputs
    timestamps_index: Optional[str] = None
    video_url: Optional[str] = None
    
    # Sprint 70: Social
    social_publish_status: str = "draft" # draft, uploaded, failed
    social_video_id: Optional[str] = None

    # Sprint 200: Captions
    caption_status: str = "none"  # none | processing | done | error
    caption_progress: float = 0.0
    caption_style: str = "karaoke"  # karaoke | word_pop | typewriter | highlight | bounce
    caption_force_whisper: bool = False
    caption_options: dict = Field(default_factory=dict)
    # Sprint 250: Parallel Tasks context
    parallel_tasks: dict[str, float] = Field(default_factory=dict)
    
    captioned_outputs: dict = Field(default_factory=dict)  # {"16:9": "storage/videos/{id}/captions/..."}  

    chapters: List[ChapterModel] = []

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "prompt": "History of Rome",
                "target_duration_minutes": 60,
                "language": "en"
            }
        }
    )
