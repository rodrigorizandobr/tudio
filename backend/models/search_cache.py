from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Dict, Any

class SearchCacheModel(BaseModel):
    id: str = Field(description="The unique key for the cache entry (provider:query)")
    data: List[Dict[str, Any]] = Field(description="The cached search results")
    provider: str = Field(description="The search provider (e.g., google, pexels, pixabay)")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
