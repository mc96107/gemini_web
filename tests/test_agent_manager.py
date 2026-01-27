import os
import shutil
import pytest
from app.core import config
from app.services.agent_manager import AgentManager
from app.models.agent import AgentModel

# Setup a temporary agent directory for testing
TEST_AGENTS_DIR = os.path.join(os.getcwd(), "tmp", "test_agents")

@pytest.fixture
def agent_manager():
    # Override config.AGENT_BASE_DIR for the test
    original_dir = config.AGENT_BASE_DIR
    config.AGENT_BASE_DIR = TEST_AGENTS_DIR
    
    # Clean setup
    if os.path.exists(TEST_AGENTS_DIR):
        shutil.rmtree(TEST_AGENTS_DIR)
    os.makedirs(TEST_AGENTS_DIR)
    
    yield AgentManager()
    
    # Teardown
    if os.path.exists(TEST_AGENTS_DIR):
        shutil.rmtree(TEST_AGENTS_DIR)
    config.AGENT_BASE_DIR = original_dir

def test_list_agents_empty(agent_manager):
    agents = agent_manager.list_agents()
    assert len(agents) == 0

def test_create_and_read_agent(agent_manager):
    agent_data = AgentModel(
        name="Dev Agent",
        description="Development helper",
        category="projects",
        folder_name="dev_helper",
        prompt="You are a dev helper."
    )
    
    # Save agent
    success = agent_manager.save_agent(agent_data)
    assert success is True
    
    # Check filesystem
    expected_path = os.path.join(TEST_AGENTS_DIR, "projects", "dev_helper", "AGENT.md")
    assert os.path.exists(expected_path)
    
    # Read agent back
    loaded_agent = agent_manager.get_agent("projects", "dev_helper")
    assert loaded_agent is not None
    assert loaded_agent.name == "Dev Agent"
    assert loaded_agent.category == "projects"
    assert loaded_agent.prompt == "You are a dev helper."

def test_list_agents_recursive(agent_manager):
    # Create multiple agents in different categories
    agent1 = AgentModel(name="A1", description="D1", category="cat1", folder_name="a1", prompt="p1")
    agent2 = AgentModel(name="A2", description="D2", category="cat2", folder_name="a2", prompt="p2")
    
    agent_manager.save_agent(agent1)
    agent_manager.save_agent(agent2)
    
    agents = agent_manager.list_agents()
    assert len(agents) == 2
    
    categories = sorted([a.category for a in agents])
    assert categories == ["cat1", "cat2"]

def test_delete_agent(agent_manager):
    agent = AgentModel(name="Del", description="To delete", category="temp", folder_name="del_me", prompt="bye")
    agent_manager.save_agent(agent)
    
    assert agent_manager.get_agent("temp", "del_me") is not None
    
    success = agent_manager.delete_agent("temp", "del_me")
    assert success is True
    
    assert agent_manager.get_agent("temp", "del_me") is None
    assert not os.path.exists(os.path.join(TEST_AGENTS_DIR, "temp", "del_me"))
