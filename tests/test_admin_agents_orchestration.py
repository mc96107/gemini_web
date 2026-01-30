import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import MagicMock, patch
from app.main import app
from app.models.agent import AgentModel

@pytest.fixture
def mock_admin_user():
    user_manager = MagicMock()
    user_manager.get_role.return_value = "admin"
    return user_manager

@pytest.fixture
def mock_agent_manager():
    return MagicMock()

@pytest.mark.anyio
async def test_toggle_agent_enabled_endpoint(mock_admin_user, mock_agent_manager):
    app.state.user_manager = mock_admin_user
    app.state.agent_manager = mock_agent_manager
    
    # Mock set_agent_enabled to return True
    mock_agent_manager.set_agent_enabled.return_value = True
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # We need to simulate a session or mock Depends(get_user)
        # For simplicity, let's patch the get_user dependency in the router
        with patch("app.routers.admin.get_user", return_value="admin_user"):
            response = await ac.post(
                "/admin/agents/functions/fabric/toggle-enabled",
                json={"enabled": True}
            )
            
    assert response.status_code == 200
    assert response.json() == {"success": True}
    mock_agent_manager.set_agent_enabled.assert_called_once_with("functions", "fabric", True)

@pytest.mark.anyio
async def test_validate_orchestration_endpoint(mock_admin_user, mock_agent_manager):
    app.state.user_manager = mock_admin_user
    app.state.agent_manager = mock_agent_manager
    
    mock_agent_manager.validate_orchestration.return_value = ["Warning 1", "Warning 2"]
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        with patch("app.routers.admin.get_user", return_value="admin_user"):
            response = await ac.get("/admin/agents/validate")
            
    assert response.status_code == 200
    assert response.json() == {"warnings": ["Warning 1", "Warning 2"]}
    mock_agent_manager.validate_orchestration.assert_called_once()
