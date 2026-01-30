import os
import pytest
import shutil
import tempfile
from unittest.mock import patch
from app.services.agent_manager import AgentManager
from app.models.agent import AgentModel

@pytest.fixture
def temp_agent_dir():
    temp_dir = tempfile.mkdtemp()
    data_agents = os.path.join(temp_dir, "data", "agents")
    os.makedirs(data_agents)
    yield temp_dir
    shutil.rmtree(temp_dir)

def test_initialize_root_orchestrator(temp_agent_dir):
    with patch('app.core.config.AGENT_BASE_DIR', os.path.join(temp_agent_dir, "data", "agents")):
        # We need to mock os.getcwd() or the part of AgentManager that uses it
        # Actually AgentManager uses config.AGENT_BASE_DIR. 
        # But root AGENT.md is at project root.
        project_root = temp_agent_dir
        
        # We need AgentManager to know about project root. 
        # Let's assume we'll add a project_root attribute or similar.
        manager = AgentManager()
        # For testing, let's explicitly set project_root if we add it
        manager.project_root = project_root
        
        manager.initialize_root_orchestrator()
        
        root_agent_path = os.path.join(project_root, "AGENT.md")
        assert os.path.exists(root_agent_path)
        
        with open(root_agent_path, "r") as f:
            content = f.read()
            agent = AgentModel.from_markdown(content, "root", "root")
            assert agent.type == "Orchestrator"

def test_set_agent_enabled(temp_agent_dir):
    with patch('app.core.config.AGENT_BASE_DIR', os.path.join(temp_agent_dir, "data", "agents")):
        project_root = temp_agent_dir
        manager = AgentManager()
        manager.project_root = project_root
        manager.initialize_root_orchestrator()
        
        # Create a dummy agent
        agent = AgentModel(
            name="Child Agent",
            description="Child",
            category="test",
            folder_name="child",
            prompt="I am a child"
        )
        manager.save_agent(agent)
        
        # Enable it
        success = manager.set_agent_enabled("test", "child", True)
        assert success
        
        # Check root AGENT.md
        root = manager.get_root_orchestrator()
        expected_path = "data/agents/test/child/AGENT.md"
        assert expected_path in root.children
        
        # Check child AGENT.md
        child = manager.get_agent("test", "child")
        assert child.parent == "AGENT.md"
        
        # Disable it
        success = manager.set_agent_enabled("test", "child", False)
        assert success
        
        # Check root again
        root = manager.get_root_orchestrator()
        assert expected_path not in root.children
        
        # Check child again
        child = manager.get_agent("test", "child")
        assert child.parent is None

def test_validate_orchestration(temp_agent_dir):
    with patch('app.core.config.AGENT_BASE_DIR', os.path.join(temp_agent_dir, "data", "agents")):
        project_root = temp_agent_dir
        manager = AgentManager()
        manager.project_root = project_root
        manager.initialize_root_orchestrator()
        
        # Create and enable agent
        agent = AgentModel(
            name="Target Agent",
            description="Target",
            category="test",
            folder_name="target",
            prompt="Target"
        )
        manager.save_agent(agent)
        manager.set_agent_enabled("test", "target", True)
        
        # Prompt doesn't mention it yet
        warnings = manager.validate_orchestration()
        assert len(warnings) > 0
        assert "Target Agent" in warnings[0]
        
        # Update prompt to mention it
        root = manager.get_root_orchestrator()
        root.prompt += "\nUse Target Agent for tests."
        manager.save_root_orchestrator(root)
        
        warnings = manager.validate_orchestration()
        assert len(warnings) == 0
