import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.routers.chat import get_user
import os
from unittest.mock import AsyncMock, MagicMock

client = TestClient(app)

# Override the get_user dependency to mock authentication
async def override_get_user():
    return "testuser"

@pytest.fixture
def mock_setup():
    # Mock the agent and conversion service in app.state
    mock_agent = AsyncMock()
    app.state.agent = mock_agent
    
    mock_conv = MagicMock()
    app.state.conversion_service = mock_conv
    
    app.dependency_overrides[get_user] = override_get_user
    yield mock_agent, mock_conv
    app.dependency_overrides.clear()

def test_chat_docx_upload_conversion(mock_setup):
    """Verify docx upload triggers conversion and uses .md path."""
    mock_agent, mock_conv = mock_setup
    
    # Setup mock conversion return value
    mock_conv.convert_to_markdown.side_effect = lambda p: p.replace(".docx", ".md")
    
    # Mock the stream generator
    async def mock_stream(*args, **kwargs):
        yield {"type": "message", "role": "assistant", "content": "Success"}
    mock_agent.generate_response_stream.return_value = mock_stream()
    mock_agent.stop_chat = AsyncMock(return_value=True)

    files = [
        ("file", ("test.docx", b"dummy docx content", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")),
    ]
    
    response = client.post(
        "/chat",
        data={"message": "hello"},
        files=files
    )
    
    assert response.status_code == 200
    
    # Check if conversion service was called
    assert mock_conv.convert_to_markdown.called
    
    # Check if agent received the .md path instead of .docx
    assert mock_agent.generate_response_stream.called
    args, kwargs = mock_agent.generate_response_stream.call_args
    file_paths = kwargs.get("file_paths", [])
    assert len(file_paths) == 1
    assert file_paths[0].endswith(".md")
    assert not file_paths[0].endswith(".docx")

def test_chat_xlsx_upload_conversion(mock_setup):
    """Verify xlsx upload triggers conversion and uses .md path."""
    mock_agent, mock_conv = mock_setup
    
    # Setup mock conversion return value
    mock_conv.convert_to_markdown.side_effect = lambda p: p.replace(".xlsx", ".md")
    
    # Mock the stream generator
    async def mock_stream(*args, **kwargs):
        yield {"type": "message", "role": "assistant", "content": "Success"}
    mock_agent.generate_response_stream.return_value = mock_stream()
    mock_agent.stop_chat = AsyncMock(return_value=True)

    files = [
        ("file", ("data.xlsx", b"dummy xlsx content", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")),
    ]
    
    response = client.post(
        "/chat",
        data={"message": "hello"},
        files=files
    )
    
    assert response.status_code == 200
    
    # Check if conversion service was called
    assert mock_conv.convert_to_markdown.called
    
    # Check if agent received the .md path
    assert mock_agent.generate_response_stream.called
    args, kwargs = mock_agent.generate_response_stream.call_args
    file_paths = kwargs.get("file_paths", [])
    assert len(file_paths) == 1
    assert file_paths[0].endswith(".md")
