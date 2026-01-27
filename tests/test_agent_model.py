import pytest
from app.models.agent import AgentModel

def test_agent_model_serialization():
    # Test that we can create an AgentModel and serialize it to AGENT.md format
    agent = AgentModel(
        name="Test Agent",
        description="A test agent",
        category="functions",
        folder_name="test_agent",
        prompt="You are a helpful assistant."
    )
    
    expected_md = """---
name: Test Agent
description: A test agent
---
You are a helpful assistant."""
    
    assert agent.to_markdown() == expected_md

def test_agent_model_from_markdown():
    # Test that we can parse an AGENT.md content into an AgentModel
    md_content = """---
name: Parsed Agent
description: A parsed agent
---
This is the system prompt."""
    
    agent = AgentModel.from_markdown(md_content, category="projects", folder_name="parsed_agent")
    
    assert agent.name == "Parsed Agent"
    assert agent.description == "A parsed agent"
    assert agent.prompt == "This is the system prompt."
    assert agent.category == "projects"
    assert agent.folder_name == "parsed_agent"
