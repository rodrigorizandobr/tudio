from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

class MusicModel(BaseModel):
    id: Optional[int] = None # Datastore ID
    
    # Metadata
    title: str
    artist: str
    genre: str
    mood: str
    
    # File info
    filename: str
    file_path: str # Relative path in storage (e.g. musics/uuid.mp3)
    duration_seconds: int = 0
    
    # Timestamps
    created_at: Optional[datetime] = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = Field(default_factory=datetime.now)
    deleted_at: Optional[datetime] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "Epic Battle",
                "artist": "Unknown",
                "genre": "Cinematic",
                "mood": "Epic",
                "filename": "battle.mp3",
                "duration_seconds": 120
            }
        }
    )
