from fastapi.testclient import TestClient
from app.main import app
from app.routers.chat import get_user
from unittest.mock import AsyncMock, patch
import pytest

def test_plan_command_recognition():
    client = TestClient(app)
    
    # Mock user login
    async def override_get_user(): return "testuser"
    app.dependency_overrides[get_user] = override_get_user
    
    # Mock generate_response_stream
    with patch("app.services.llm_service.GeminiAgent.generate_response_stream") as mock_stream:
        # Create an async generator mock
        async def mock_gen(*args, **kwargs):
            yield {"type": "message", "content": "Planning..."}
            yield {"type": "done"}
            
        mock_stream.side_effect = mock_gen
        
        response = client.post("/chat", data={"message": "/plan design a new feature"})
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]
        
        # Verify call arguments
        call_args = mock_stream.call_args
        assert call_args.kwargs["plan_mode"] is True
        assert call_args.args[1] == "design a new feature"
    
    del app.dependency_overrides[get_user]

def test_plan_command_toggles_mode():
    client = TestClient(app)
    # Mock user login
    async def override_get_user(): return "testuser"
    app.dependency_overrides[get_user] = override_get_user
    
    # This might need GeminAgent to have a plan_mode attribute or similar
    # or it just passes a flag to generate_response_stream.
    pass
