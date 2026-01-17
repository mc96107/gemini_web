import pytest
import asyncio
import json
from fastapi.testclient import TestClient
from app.main import app
from unittest.mock import MagicMock, patch

@pytest.fixture
def anyio_backend():
    return 'asyncio'

def test_stop_endpoint_directly(anyio_backend):
    # Mock dependency override for get_user in chat router
    from app.routers.chat import get_user
    app.dependency_overrides[get_user] = lambda: "testuser"
    
    try:
        client = TestClient(app)
        
        # 1. No active task
        response = client.post("/stop")
        assert response.status_code == 200
        assert response.json() == {"success": False}
        
        # 2. Simulate an active task
        # We need a mock that is awaitable
        class AwaitableMock(MagicMock):
            def __await__(self):
                # Return an iterator that raises CancelledError
                yield
                raise asyncio.CancelledError()

        mock_task = AwaitableMock()
        mock_task.done.return_value = False
        
        app.state.agent.active_tasks["testuser"] = mock_task
        
        response = client.post("/stop")
        assert response.status_code == 200
        assert response.json() == {"success": True}
        assert mock_task.cancel.called
    finally:
        app.dependency_overrides.clear()
        if "testuser" in app.state.agent.active_tasks:
            del app.state.agent.active_tasks["testuser"]
