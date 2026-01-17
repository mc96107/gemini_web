import pytest
from fastapi.testclient import TestClient
from app.main import app
from unittest.mock import patch, MagicMock, AsyncMock

client = TestClient(app)

@pytest.fixture
def mock_user(monkeypatch):
    def mock_get_user():
        return "test_user"
    from app.routers.chat import get_user
    app.dependency_overrides[get_user] = mock_get_user
    yield "test_user"
    app.dependency_overrides = {}

@pytest.fixture
def anyio_backend():
    return 'asyncio'

@pytest.mark.anyio
async def test_rename_chat_endpoint(mock_user):
    session_uuid = "test-session-uuid"
    new_title = "New Chat Title"
    
    # Mock the agent
    mock_agent = MagicMock()
    mock_agent.update_session_title = AsyncMock(return_value=True)
    app.state.agent = mock_agent
    
    response = client.post(
        f"/sessions/{session_uuid}/title",
        json={"title": new_title}
    )
    
    if response.status_code != 200:
        print(response.json())
    assert response.status_code == 200
    assert response.json() == {"success": True}
    mock_agent.update_session_title.assert_called_once_with("test_user", session_uuid, new_title)

@pytest.mark.anyio
async def test_rename_chat_not_found(mock_user):
    session_uuid = "non-existent-uuid"
    new_title = "New Chat Title"
    
    # Mock the agent
    mock_agent = MagicMock()
    mock_agent.update_session_title = AsyncMock(return_value=False)
    app.state.agent = mock_agent
    
    response = client.post(
        f"/sessions/{session_uuid}/title",
        json={"title": new_title}
    )
    
    assert response.status_code == 404
