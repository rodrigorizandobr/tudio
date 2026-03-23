
import pytest
from unittest.mock import MagicMock, patch
from backend.services.agent_service import AgentService
from backend.models.agent import AgentModel

class TestAgentService:
    @pytest.fixture
    def service(self):
        svc = AgentService()
        svc.repository = MagicMock()
        return svc

    def test_create(self, service):
        agent = AgentModel(name="Test")
        service.repository.save.return_value = agent
        
        saved = service.create(agent)
        assert saved == agent
        service.repository.save.assert_called_once()

    def test_update_existing(self, service):
        existing = AgentModel(id="1", name="Old")
        service.repository.get.return_value = existing
        service.repository.save.return_value = existing
        
        update_data = AgentModel(name="New")
        updated = service.update("1", update_data)
        
        assert updated.name == "New"
        service.repository.save.assert_called_once()

    def test_update_not_found(self, service):
        service.repository.get.return_value = None
        
        updated = service.update("999", AgentModel(name="test"))
        assert updated is None
        service.repository.save.assert_not_called()

    def test_ensure_default_agent_created(self, service):
        service.repository.list_all.return_value = []
        service.repository.save.return_value = MagicMock(id="default")
        
        service.ensure_default_agent()
        
        service.repository.save.assert_called_once()
        args, _ = service.repository.save.call_args
        assert args[0].is_default is True

    def test_ensure_default_agent_exists(self, service):
        service.repository.list_all.return_value = [AgentModel(name="Existing")]
        
        service.ensure_default_agent()
        
        service.repository.save.assert_not_called()
