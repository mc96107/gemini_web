from fastapi.testclient import TestClient
from app.main import app
from app.routers.chat import get_user
import pytest
from unittest.mock import MagicMock, AsyncMock

@pytest.fixture
def auth_client():
    # Mock the dependency
    def mock_get_user():
        return "test_user"
    
    original_overrides = app.dependency_overrides.copy()
    app.dependency_overrides[get_user] = mock_get_user
    
    # Save original state to restore later
    original_has_users = app.state.user_manager.has_users
    original_get_role = app.state.user_manager.get_role
    original_get_user_sessions = app.state.agent.get_user_sessions
    original_get_session_messages = app.state.agent.get_session_messages
    
    yield TestClient(app)
    
    # Restore
    app.dependency_overrides = original_overrides
    app.state.user_manager.has_users = original_has_users
    app.state.user_manager.get_role = original_get_role
    app.state.agent.get_user_sessions = original_get_user_sessions
    app.state.agent.get_session_messages = original_get_session_messages

def test_header_mobile_dropdown_exists(auth_client):
    # Mock user_manager.has_users() and get_role()
    app.state.user_manager.has_users = MagicMock(return_value=True)
    app.state.user_manager.get_role = MagicMock(return_value="admin")
    
    # Mock agent async methods
    app.state.agent.get_user_sessions = AsyncMock(return_value=[{"uuid": "test-uuid", "active": True, "title": "Test Chat"}])
    app.state.agent.get_session_messages = AsyncMock(return_value=[])
    
    response = auth_client.get("/")
    assert response.status_code == 200
    assert 'id="mobile-actions-dropdown"' in response.text