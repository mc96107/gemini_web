import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core import config
import os
import shutil

client = TestClient(app)

@pytest.fixture
def mock_admin(monkeypatch):
    # Mock the get_user dependency or the session to act as admin
    # In app/routers/admin.py: 
    # async def get_user(request: Request): return request.session.get("user")
    # user_manager.get_role(user) == "admin"
    
    # We can mock the session by using a cookie or by overriding the dependency
    from app.routers.admin import get_user
    async def override_get_user():
        return "admin_user"
    
    app.dependency_overrides[get_user] = override_get_user
    
    # Also need to mock user_manager.get_role
    original_user_manager = app.state.user_manager
    class MockUserManager:
        def get_role(self, user):
            return "admin"
        def get_all_users(self): return []
    
    app.state.user_manager = MockUserManager()
    
    yield
    
    app.dependency_overrides.pop(get_user)
    app.state.user_manager = original_user_manager

def test_admin_agents_unauthorized():
    # Test that non-admin or unauthenticated cannot access
    response = client.get("/admin/agents")
    # Depending on implementation, it might redirect or return 403
    # admin router usually redirects if get_user returns None
    assert response.status_code in [303, 403]

def test_list_agents_api(mock_admin):
    response = client.get("/admin/agents")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_create_agent_api(mock_admin):
    agent_json = {
        "name": "API Agent",
        "description": "Created via API",
        "category": "systems",
        "folder_name": "api_agent",
        "prompt": "API Prompt"
    }
    response = client.post("/admin/agents", json=agent_json)
    assert response.status_code == 200
    assert response.json()["success"] is True

def test_get_agent_api(mock_admin):
    # Ensure agent exists first
    agent_json = {
        "name": "Fetch Me",
        "description": "Fetch Test",
        "category": "functions",
        "folder_name": "fetch_test",
        "prompt": "Fetch Prompt"
    }
    client.post("/admin/agents", json=agent_json)
    
    response = client.get("/admin/agents/functions/fetch_test")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Fetch Me"
    assert data["prompt"] == "Fetch Prompt"

def test_delete_agent_api(mock_admin):
    # Ensure agent exists first
    agent_json = {
        "name": "To Delete",
        "description": "Delete Test",
        "category": "temp",
        "folder_name": "api_del",
        "prompt": "Bye"
    }
    client.post("/admin/agents", json=agent_json)
    
    response = client.delete("/admin/agents/temp/api_del")
    assert response.status_code == 200
    assert response.json()["success"] is True
    
    # Verify it's gone
    response = client.get("/admin/agents/temp/api_del")
    assert response.status_code == 404
