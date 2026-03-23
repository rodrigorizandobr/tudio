import pytest
from backend.repositories.agent_repository import agent_repository
from backend.models.agent import AgentModel
from unittest.mock import patch

# --- Integration Fixtures ---
from backend.tests.fakes.fake_datastore import FakeDatastoreClient

@pytest.fixture(scope="module")
def fake_db():
    return FakeDatastoreClient()

@pytest.fixture(autouse=True)
def patch_datastore(fake_db):
    # Patch the repository's access to the client
    with patch("backend.repositories.agent_repository.get_datastore_client", return_value=fake_db):
        yield

@pytest.fixture
def clean_datastore(fake_db):
    yield
    fake_db._storage.clear()

# --- Tests ---

def test_create_and_get_agent(clean_datastore):
    """Test CRUD basics: create and retrieve agent"""
    # Create agent
    agent = AgentModel(
        name="Test Agent",
        description="Test description",
        icon="Bot",
        prompt_init="Test init prompt",
        is_default=False
    )
    
    saved_agent = agent_repository.save(agent)
    
    # Verify ID assigned
    assert saved_agent.id is not None
    assert saved_agent.name == "Test Agent"
    
    # Retrieve
    retrieved = agent_repository.get(saved_agent.id)
    assert retrieved is not None
    assert retrieved.id == saved_agent.id
    assert retrieved.name == "Test Agent"
    assert retrieved.description == "Test description"
    assert retrieved.prompt_init == "Test init prompt"

def test_list_agents(clean_datastore):
    """Test listing all agents"""
    # Create multiple agents
    agent1 = AgentModel(name="Agent 1", icon="Bot")
    agent2 = AgentModel(name="Agent 2", icon="User")
    
    agent_repository.save(agent1)
    agent_repository.save(agent2)
    
    # List all
    agents = agent_repository.list_all()
    assert len(agents) >= 2
    names = [a.name for a in agents]
    assert "Agent 1" in names
    assert "Agent 2" in names

def test_find_by_name(clean_datastore):
    """Test finding agent by name"""
    # Create agent
    agent = AgentModel(name="Unique Agent", icon="Sparkles")
    agent_repository.save(agent)
    
    # Find by name
    found = agent_repository.find_by_name("Unique Agent")
    assert found is not None
    assert found.name == "Unique Agent"
    
    # Not found
    not_found = agent_repository.find_by_name("Nonexistent Agent")
    assert not_found is None

def test_update_agent(clean_datastore):
    """Test updating existing agent"""
    # Create
    agent = AgentModel(name="Original Name", icon="Bot")
    saved = agent_repository.save(agent)
    original_id = saved.id
    
    # Update
    saved.name = "Updated Name"
    saved.description = "New description"
    updated = agent_repository.save(saved)
    
    # Verify ID unchanged
    assert updated.id == original_id
    
    # Retrieve and verify
    retrieved = agent_repository.get(original_id)
    assert retrieved.name == "Updated Name"
    assert retrieved.description == "New description"

def test_delete_agent(clean_datastore):
    """Test deleting agent"""
    # Create
    agent = AgentModel(name="To Delete", icon="Trash")
    saved = agent_repository.save(agent)
    agent_id = saved.id
    
    # Verify exists
    assert agent_repository.get(agent_id) is not None
    
    # Delete
    result = agent_repository.delete(agent_id)
    assert result is True
    
    # Verify deleted
    deleted = agent_repository.get(agent_id)
    assert deleted is None

def test_agent_with_large_prompts(clean_datastore):
    """Test saving agent with large prompt fields (exclude from indexes)"""
    # Create agent with large prompt
    large_prompt = "A" * 2000  # Larger than 1500 bytes limit
    
    agent = AgentModel(
        name="Large Agent",
        icon="FileText",
        prompt_init=large_prompt,
        prompt_chapters=large_prompt,
        prompt_subchapters=large_prompt,
        prompt_scenes=large_prompt,
        description="A" * 2000
    )
    
    saved = agent_repository.save(agent)
    
    # Retrieve and verify
    retrieved = agent_repository.get(saved.id)
    assert retrieved is not None
    assert len(retrieved.prompt_init) == 2000
    assert len(retrieved.description) == 2000

def test_default_agent_flag(clean_datastore):
    """Test is_default flag"""
    # Create default agent
    default_agent = AgentModel(name="Default", icon="Star", is_default=True)
    agent_repository.save(default_agent)
    
    # Create non-default
    regular_agent = AgentModel(name="Regular", icon="Bot", is_default=False)
    agent_repository.save(regular_agent)
    
    # List and verify
    agents = agent_repository.list_all()
    default_agents = [a for a in agents if a.is_default]
    regular_agents = [a for a in agents if not a.is_default]
    
    assert len(default_agents) >= 1
    assert len(regular_agents) >= 1
