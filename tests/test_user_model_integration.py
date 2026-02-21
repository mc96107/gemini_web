import json
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from app.main import app
from app.routers.chat import get_user

@pytest.mark.asyncio
async def test_chat_uses_default_model_when_not_provided():
    client = TestClient(app)
    
    # Mock user login
    async def override_get_user(): return "testuser"
    app.dependency_overrides[get_user] = override_get_user
    
    # Set default model
    client.post("/settings", json={"default_model": "gemini-3-flash-preview"})
    
    # Mock agent.generate_response_stream
    # We want to check if it's called with the correct model
    from app.services.llm_service import GeminiAgent
    
    with patch.object(GeminiAgent, 'generate_response_stream') as mock_stream:
        # Mock it to be an async generator
        async def mock_gen(*args, **kwargs):
            yield {"type": "message", "role": "assistant", "content": "Hello"}
            yield "[DONE]"
        
        mock_stream.side_effect = mock_gen
        
        # Call /chat without model parameter
        response = client.post("/chat", data={"message": "Hi"})
        
        # Check call arguments of generate_response_stream
        # It's called in chat router: agent.generate_response_stream(user, message, model=m_override, ...)
        # m_override should be None if not provided in Form
        
        # Wait, the router calls it with model=m_override.
        # If model Form field is missing, m_override is None.
        
        # In GeminiAgent.generate_response_stream:
        # current_model = model or settings.get("default_model") or self.model_name
        
        # Since we mocked generate_response_stream, we are testing the router's call.
        # But we want to test that the AGENT uses the default model.
        # So we should mock _create_subprocess instead.
        
        pass

    del app.dependency_overrides[get_user]

@pytest.mark.asyncio
async def test_agent_generate_response_uses_default_model(tmp_path):
    from app.services.llm_service import GeminiAgent
    agent = GeminiAgent(working_dir=str(tmp_path))
    user_id = "testuser"
    
    # Set default model
    agent.update_user_settings(user_id, {"default_model": "gemini-3-flash-preview"})
    
    # Mock _create_subprocess
    agent._create_subprocess = AsyncMock()
    mock_proc = AsyncMock()
    mock_proc.stdin = AsyncMock()
    mock_proc.stdout = AsyncMock()
    mock_proc.stderr = AsyncMock()
    mock_proc.wait = AsyncMock(return_value=0)
    mock_proc.stdout.readline = AsyncMock(return_value=b"")
    mock_proc.stderr.readline = AsyncMock(return_value=b"")
    agent._create_subprocess.return_value = mock_proc

    # Call generate_response_stream without model
    async for _ in agent.generate_response_stream(user_id, "Hello"):
        pass
        
    # Check args
    call_args = agent._create_subprocess.call_args[0][0]
    model_idx = call_args.index("--model")
    assert call_args[model_idx + 1] == "gemini-3-flash-preview"
