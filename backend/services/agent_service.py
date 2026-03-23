from typing import List, Optional
from backend.repositories.agent_repository import agent_repository
from backend.models.agent import AgentModel
from backend.core.configs import settings
from backend.core.logger import log

class AgentService:
    def __init__(self):
        self.repository = agent_repository

    async def create(self, agent: AgentModel) -> AgentModel:
        return await self.repository.save(agent)

    async def update(self, agent_id: str, agent_data: AgentModel) -> Optional[AgentModel]:
        existing = await self.repository.get(agent_id)
        if not existing:
            return None
        
        # Update fields
        existing.name = agent_data.name
        existing.description = agent_data.description
        existing.icon = agent_data.icon
        existing.prompt_init = agent_data.prompt_init
        existing.prompt_chapters = agent_data.prompt_chapters
        existing.prompt_subchapters = agent_data.prompt_subchapters
        existing.prompt_scenes = agent_data.prompt_scenes
        existing.prompt_image_search = agent_data.prompt_image_search
        
        return await self.repository.save(existing)

    async def delete(self, agent_id: str) -> bool:
        return await self.repository.delete(agent_id)

    async def get(self, agent_id: str) -> Optional[AgentModel]:
        return await self.repository.get(agent_id)

    async def list_all(self) -> List[AgentModel]:
        return await self.repository.list_all()

    async def get_default(self) -> Optional[AgentModel]:
        return await self.repository.find_default()

    async def ensure_default_agent(self):
        """
        Checks if any agent exists. If not, creates a 'Default' agent
        using the prompts currently defined in settings (.env).
        """
        all_agents = await self.list_all()
        if not all_agents:
            log.info("No agents found. Migrating default prompts from settings...")
            
            default_agent = AgentModel(
                name="Padrão",
                description="Agente padrão sistema.",
                prompt_init=settings.PROMPT_INIT_TEMPLATE,

                prompt_chapters=settings.PROMPT_CHAPTERS_TEMPLATE,
                prompt_subchapters=settings.PROMPT_SUBCHAPTERS_TEMPLATE,
                prompt_scenes=settings.PROMPT_SCENES_TEMPLATE,
                prompt_image_search=settings.PROMPT_IMAGE_SEARCH_TEMPLATE,
                is_default=True
            )
            
            saved = await self.create(default_agent)
            log.info(f"Default agent created with ID: {saved.id}")
        else:
            log.info(f"Agents already exist ({len(all_agents)}). Skipping default migration.")

agent_service = AgentService()
