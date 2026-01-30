import pytest
from app.models.agent import AgentModel

def test_agent_model_orchestration_fields():
    """Test that the new orchestration fields exist and have default values."""
    agent = AgentModel(
        name="Test Agent",
        slug="test-agent",
        description="A test agent",
        category="test_category",
        folder_name="test_folder",
        prompt="You are a test agent."
    )
    
    # Check default values
    assert agent.type == "FunctionAgent"
    assert agent.children == []
    assert agent.parent is None
    assert agent.used_by == []

def test_agent_model_serialization_wikilinks():
    """Test that fields are serialized/deserialized with Wiki-link format."""
    
    markdown_content = """---
type: Orchestrator
children: [[data/agents/child1.md], [data/agents/child2.md]]
parent: [[root/AGENT.md]]
used_by: [[system/core_agent.md]]
---
# Test Agent

This is a test agent.
"""
    
    agent = AgentModel.from_markdown(markdown_content, category="test", folder_name="agent")
    
    assert agent.type == "Orchestrator"
    assert "data/agents/child1.md" in agent.children
    assert "data/agents/child2.md" in agent.children
    assert agent.parent == "root/AGENT.md"
    assert "system/core_agent.md" in agent.used_by
    
    # Test round-trip serialization
    output_md = agent.to_markdown()
    assert "type: Orchestrator" in output_md
    assert "children: [[data/agents/child1.md], [data/agents/child2.md]]" in output_md
    assert "parent: [[root/AGENT.md]]" in output_md
    assert "used_by: [[system/core_agent.md]]" in output_md

def test_agent_model_legacy_compatibility():
    """Test that legacy agents without new fields still load correctly."""
    markdown_content = """---
description: Legacy agent
---
# Legacy Agent
Legacy prompt
"""
    agent = AgentModel.from_markdown(markdown_content, category="legacy", folder_name="agent")
    assert agent.type == "FunctionAgent"  # Default
    assert agent.children == []
    assert agent.parent is None