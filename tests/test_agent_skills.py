from fastapi.testclient import TestClient
from app.main import app
from app.routers.admin import get_user
from app.core import config
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
    
    # Ensure skills dir exists and has a file
    skills_dir = config.SKILLS_BASE_DIR
    skill_name = "test-skill"
    test_skill_dir = os.path.join(skills_dir, skill_name)
    os.makedirs(test_skill_dir, exist_ok=True)
    with open(os.path.join(test_skill_dir, "SKILL.md"), "w") as f:
        f.write("# Test Skill")
    
    try:
        response = client.get("/admin/skills")
        assert response.status_code == 200
        data = response.json()
        assert skill_name in data
    finally:
        shutil.rmtree(test_skill_dir)
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
