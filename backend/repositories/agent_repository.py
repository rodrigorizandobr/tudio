import asyncio
from typing import List, Optional
from datetime import datetime
from google.cloud import datastore
from backend.core.datastore_client import get_datastore_client
from backend.models.agent import AgentModel

class AgentRepository:
    def __init__(self):
        self.kind = "Agent"

    @property
    def client(self) -> datastore.Client:
        return get_datastore_client()

    async def save(self, agent: AgentModel) -> AgentModel:
        return await asyncio.to_thread(self._save_sync, agent)

    def _save_sync(self, agent: AgentModel) -> AgentModel:
        client = self.client
        agent.updated_at = datetime.now()
        
        if agent.id:
            try:
                key_id = int(agent.id)
            except ValueError:
                key_id = agent.id
            key = client.key(self.kind, key_id)
        else:
            key = client.key(self.kind)

        entity = datastore.Entity(key=key)
        data = agent.model_dump(exclude={"id"}, mode="json")
        entity.update(data)
        
        large_fields = ["prompt_init", "prompt_chapters", "prompt_subchapters", "prompt_scenes", "description"]
        current_excluded = set(entity.exclude_from_indexes)
        current_excluded.update(large_fields)
        entity.exclude_from_indexes = list(current_excluded)
        
        client.put(entity)
        if not agent.id:
            agent.id = str(entity.key.id)
        return agent

    async def get(self, agent_id: str) -> Optional[AgentModel]:
        return await asyncio.to_thread(self._get_sync, agent_id)

    def _get_sync(self, agent_id: str) -> Optional[AgentModel]:
        client = self.client
        try:
            key_id = int(agent_id)
        except ValueError:
            key_id = agent_id
        key = client.key(self.kind, key_id)
        entity = client.get(key)
        if not entity: return None
        data = dict(entity)
        data["id"] = str(entity.key.id)
        return AgentModel(**data)

    async def list_all(self) -> List[AgentModel]:
        return await asyncio.to_thread(self._list_all_sync)

    def _list_all_sync(self) -> List[AgentModel]:
        client = self.client
        query = client.query(kind=self.kind)
        query.order = ["created_at"]
        results = list(query.fetch())
        agents = []
        for entity in results:
            data = dict(entity)
            data["id"] = str(entity.key.id)
            agents.append(AgentModel(**data))
        return agents

    async def delete(self, agent_id: str) -> bool:
        return await asyncio.to_thread(self._delete_sync, agent_id)

    def _delete_sync(self, agent_id: str) -> bool:
        client = self.client
        try:
            key_id = int(agent_id)
        except ValueError:
            key_id = agent_id
        key = client.key(self.kind, key_id)
        client.delete(key)
        return True

    async def find_by_name(self, name: str) -> Optional[AgentModel]:
        return await asyncio.to_thread(self._find_by_name_sync, name)

    def _find_by_name_sync(self, name: str) -> Optional[AgentModel]:
        client = self.client
        query = client.query(kind=self.kind)
        query.add_filter("name", "=", name)
        results = list(query.fetch(limit=1))
        if results:
            data = dict(results[0])
            data["id"] = str(results[0].key.id)
            return AgentModel(**data)
        return None

    async def find_default(self) -> Optional[AgentModel]:
        return await asyncio.to_thread(self._find_default_sync)

    def _find_default_sync(self) -> Optional[AgentModel]:
        client = self.client
        query = client.query(kind=self.kind)
        query.add_filter("is_default", "=", True)
        results = list(query.fetch(limit=1))
        if results:
            data = dict(results[0])
            data["id"] = str(results[0].key.id)
            return AgentModel(**data)
        return None

agent_repository = AgentRepository()
