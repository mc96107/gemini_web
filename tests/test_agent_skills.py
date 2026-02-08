from fastapi.testclient import TestClient
from app.main import app
from app.routers.admin import get_user
from app.models.agent import AgentModel
from unittest.mock import patch, MagicMock
import os
import shutil
import pytest

def test_admin_skills_list():
    client = TestClient(app)
    # Mock admin login
    async def override_get_admin(): return "admin"
    app.dependency_overrides[get_user] = override_get_admin
    
    # Ensure .agents/skills exists and has a file
    os.makedirs(".agents/skills", exist_ok=True)
    with open(".agents/skills/test-skill.md", "w") as f:
        f.write("# Test Skill")
    
    try:
        response = client.get("/admin/skills")
        assert response.status_code == 200
        data = response.json()
        assert "test-skill" in data
    finally:
        os.remove(".agents/skills/test-skill.md")
        del app.dependency_overrides[get_user]

def test_agent_model_with_skills():
    md = """---
name: Test Agent
description: A test agent
type: FunctionAgent
skills:
  - code-reviewer
  - tester
---
Hello world"""
    agent = AgentModel.from_markdown(md, "test", "test_folder")
    assert agent.skills == ["code-reviewer", "tester"]
    
    serialized = agent.to_markdown()
    assert "skills:" in serialized
    assert "- code-reviewer" in serialized
    assert "- tester" in serialized
