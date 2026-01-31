import pytest
from app.models.agent import AgentModel, AgentLink

def test_agent_model_orchestration_fields():
    """Test that the new orchestration fields exist and have default values."""
    agent = AgentModel(
        name="Test Agent",
        description="A test agent",
        category="test_category",
        folder_name="test_folder",
        prompt="You are a test agent."
    )
    
    # Check default values
    assert agent.type == "FunctionAgent"
    assert agent.children == []
    assert agent.uses == []
    assert agent.projects == []
    assert agent.parent is None
    assert agent.used_by == []

def test_agent_model_complex_orchestrator():
    """Test parsing a complex orchestrator with multi-line lists and comments."""
    
    markdown_content = """---
id: orchestrator
type: Orchestrator
description: Lead agent for E/M.
children:
- '[[data/agents/systems/electrical/AGENT.md]]' # Comment 1
- '[[data/agents/systems/hvac/AGENT.md]]' # Comment 2
uses:
- '[[data/agents/functions/fabric/AGENT.md]]'
projects:
- [[data/agents/projects/p1/AGENT.md]]
---
# Prompt
"""
    
    agent = AgentModel.from_markdown(markdown_content, category="test", folder_name="agent")
    
    assert agent.id == "orchestrator"
    assert agent.type == "Orchestrator"
    
    child_paths = [c.path for c in agent.children]
    assert "data/agents/systems/electrical/AGENT.md" in child_paths
    assert "data/agents/systems/hvac/AGENT.md" in child_paths
    
    # Check descriptions
    assert agent.children[0].description == "Comment 1"
    
    assert agent.uses[0].path == "data/agents/functions/fabric/AGENT.md"
    assert agent.projects[0].path == "data/agents/projects/p1/AGENT.md"
    
    # Test round-trip serialization
    output_md = agent.to_markdown()
    assert "id: orchestrator" in output_md
    assert "children:" in output_md
    assert "  - [[data/agents/systems/electrical/AGENT.md]] # Comment 1" in output_md

def test_agent_model_sub_agent():
    """Test parsing a sub-agent with multi-line used_by and parent."""
    markdown_content = """---
id: function_compliance
type: FunctionAgent
description: Verifies designs.
parent: [[../../../../AGENT.md]]
used_by:
  - [[data/agents/systems/electrical/AGENT.md]]
  - [[data/agents/systems/hvac/AGENT.md]]
---
# Prompt
"""
    agent = AgentModel.from_markdown(markdown_content, category="test", folder_name="agent")
    assert agent.id == "function_compliance"
    assert agent.parent == "../../../../AGENT.md"
    assert "data/agents/systems/electrical/AGENT.md" in agent.used_by
    assert "data/agents/systems/hvac/AGENT.md" in agent.used_by

def test_agent_model_legacy_compatibility():
    """Test that legacy agents without new fields still load correctly."""
    markdown_content = """---
description: Legacy agent
---
# Legacy Agent
Legacy prompt
"""
    agent = AgentModel.from_markdown(markdown_content, category="legacy", folder_name="agent")
    assert agent.type == "FunctionAgent"
    assert agent.children == []
    assert agent.parent is None