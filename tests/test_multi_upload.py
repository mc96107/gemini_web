import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.routers.chat import get_user
import os
import json
from unittest.mock import AsyncMock, patch

client = TestClient(app)

# Override the get_user dependency to mock authentication
async def override_get_user():
    return "testuser"

@pytest.fixture
def mock_agent():
    # Mock the agent in app.state
    mock = AsyncMock()
    app.state.agent = mock
    app.dependency_overrides[get_user] = override_get_user
    yield mock
    app.dependency_overrides.clear()

def test_chat_multi_file_upload(mock_agent):
    """Verify chat router handles multiple files."""
    
    # Create dummy files
    files = [
        ("file", ("test1.txt", b"content1", "text/plain")),
        ("file", ("test2.txt", b"content2", "text/plain")),
        ("file", ("test3.txt", b"content3", "text/plain")),
    ]
    
    # Mock the stream generator
    async def mock_stream(*args, **kwargs):
        yield {"type": "message", "role": "assistant", "content": "Success"}
        
    mock_agent.generate_response_stream.return_value = mock_stream()
    mock_agent.stop_chat = AsyncMock(return_value=True)
    
    response = client.post(
        "/chat",
        data={"message": "hello", "model": "gemini-3-pro-preview"},
        files=files
    )
    
    assert response.status_code == 200
    
    # Consume stream
    for line in response.iter_lines():
        pass

    # Check if generate_response_stream was called with a list of 3 file paths
    assert mock_agent.generate_response_stream.called
    args, kwargs = mock_agent.generate_response_stream.call_args
    assert "file_paths" in kwargs
    assert len(kwargs["file_paths"]) == 3
    assert any("test1.txt" in fp for fp in kwargs["file_paths"])
    assert any("test2.txt" in fp for fp in kwargs["file_paths"])
    assert any("test3.txt" in fp for fp in kwargs["file_paths"])