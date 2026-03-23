import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

# Base path is the project root
BASE_PATH = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class Settings(BaseSettings):
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Tudio V2 - Video Generator"
    
    # Base path field (optional if just used for logic, but good to keep)
    BASE_PATH: str = BASE_PATH
    
    # Centralized Storage
    STORAGE_DIR: str = os.path.join(BASE_PATH, "storage")
    LOG_DIR: str = os.path.join(STORAGE_DIR, "logs")
    DATA_DIR: str = os.path.join(STORAGE_DIR, "data")
    CACHE_DIR: str = os.path.join(STORAGE_DIR, "cache")
    
    # Image Search Cache
    IMAGE_SEARCH_CACHE_EXPIRATION_DAYS: int = 180  # Cache expires after 180 days (6 months)

    # Audio/Video Defaults
    DEFAULT_AUDIO_PADDING_SECONDS: float = 0.5



    # Credentials / Secrets
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-3.5-turbo"
    OPENAI_MAX_RETRIES: int = 1  # Maximum retries on thread corruption (0 = no retry)
    UNSPLASH_ACCESS_KEY: Optional[str] = None
    SERPAPI_API_KEY: Optional[str] = None
    PEXELS_API_KEY: Optional[str] = None
    PIXABAY_API_KEY: Optional[str] = None
    
    # Proxy Configuration
    USE_PROXY: bool = False
    PROXY_TYPE: str = "socks5"  # socks5, http, https, none
    PROXY_HOST: str = "localhost"
    PROXY_PORT: int = 1080
    PROXY_USERNAME: Optional[str] = None
    PROXY_PASSWORD: Optional[str] = None
    NO_PROXY_DOMAINS: str = "localhost,127.0.0.1"
    VERIFY_SSL: bool = True

    # Environment & Infrastructure
    APP_ENV: str = "dev"  # dev, hml, prd
    TESTING: bool = False
    
    @property
    def GOOGLE_CLOUD_PROJECT(self) -> str:
        env_map = {
            "dev": "tudio-dev",
            "hml": "tudio-hml",
            "prd": "tudio-prd"
        }
        return env_map.get(self.APP_ENV, "tudio-dev")
    
    # Authentication & Security
    JWT_SECRET_KEY: str = "CHANGE_ME_IN_PRD_SECRET_KEY" # Should be loaded from env
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 # 24 hours

    # Social Networks (Google/YouTube)
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/v1/social/auth/callback"



    # Prompts (Loaded from .env)
    PROMPT_INIT_TEMPLATE: str = ""
    PROMPT_CHAPTERS_TEMPLATE: str = ""
    PROMPT_SUBCHAPTERS_TEMPLATE: str = ""
    PROMPT_SCENES_TEMPLATE: str = ""
    PROMPT_SCRIPT_TO_VIDEO_TEMPLATE: str = """Organize the provided script scenes into logical Chapters and Subchapters.
    
    CRITICAL REQUIREMENTS:
    1. You MUST include EVERY SINGLE scene provided in the 'scenes_list'.
    2. Do NOT merge, skip, summarize, or omit any scene.
    3. Do NOT modify the 'narration_content' of any scene. It must be identical to the original.
    4. Group the provided scenes into 1 or more Chapters and Subchapters.
    5. Maintain the exact 'id' for each scene as provided in the list.
    6. For each scene, generate visual enrichment (prompts, search terms).
    
    Context: {context}
    Provided Scenes: {scenes_list}
    
    Schema JSON OBRIGATÓRIO:
    {{
      'chapters': [
        {{
          'id': int, 'order': int, 'title': 'string', 'description': 'string',
          'subchapters': [
            {{
              'id': int, 'order': int, 'title': 'string', 'description': 'string',
              'scenes': [
                 {{
                   'id': int, 'order': int, 'narration_content': 'EXACT ORIGINAL TEXT',
                   'visual_description': 'string', 'image_prompt': 'string', 
                   'video_prompt': 'string', 'image_search': 'string', 
                   'video_search': 'string', 'audio_search': 'string'
                 }}
              ]
            }}
          ]
        }}
      ]
    }}"""

    PROMPT_IMAGE_SEARCH_TEMPLATE: str = """No images found for search term: '{original_query}'.
Context: {context}
Failed Terms: {failed_terms}

Return a JSON object with a property "terms" containing a list of 5 alternative search terms (synonyms, simplified concepts, related objects) sorted by priority (most likely to find a stock photo first).
Avoid terms listed in Failed Terms.
Format: {"terms": ["term1", "term2", "term3", "term4", "term5"]}"""

    model_config = SettingsConfigDict(
        case_sensitive=True,
        env_file=os.path.join(BASE_PATH, ".env"),
        extra="ignore"
    )

settings = Settings()
