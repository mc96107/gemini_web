import pytest
import os
from fastapi.testclient import TestClient
from app.main import app
from unittest.mock import AsyncMock, patch, MagicMock

client = TestClient(app)

# Mocking the session is tricky with Starlette's SessionMiddleware.
# We'll override the get_user dependency.
from app.routers.prompt_helper import get_user

@pytest.fixture
def override_auth():
    app.dependency_overrides[get_user] = lambda: "test_user"
    yield
    app.dependency_overrides.clear()

def test_get_session_empty(override_auth):
    # We still need to mock request.session.get in the endpoint or the session state
    with patch("fastapi.Request.session", new_callable=MagicMock) as mock_session:
        mock_session.get.return_value = None
        response = client.get("/api/prompt-helper/session")
        assert response.status_code == 200
        assert response.json() == {"session": None}

@patch("app.services.tree_prompt_service.TreePromptService.generate_next_question", new_callable=AsyncMock)
def test_start_session(mock_gen, override_auth):
    mock_gen.return_value = {
        "question": "What is the topic?",
        "options": ["A", "B"],
        "reasoning": "Reason",
        "is_complete": False
    }
    
    # Mock session to store session_id
    with patch("starlette.requests.Request.session", new_callable=PropertyMock) as mock_session_prop:
        mock_session = {}
        mock_session_prop.return_value = mock_session
        
        response = client.post("/api/prompt-helper/start")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "session_id" in data
        assert mock_session["prompt_tree_session_id"] == data["session_id"]

@patch("app.services.tree_prompt_service.TreePromptService.generate_next_question", new_callable=AsyncMock)
def test_answer_question(mock_gen, override_auth):
    mock_gen.return_value = {"question": "Q2", "is_complete": False}
    
    with patch("starlette.requests.Request.session", new_callable=PropertyMock) as mock_session_prop:
        mock_session = {"prompt_tree_session_id": "fake_session_id"}
        mock_session_prop.return_value = mock_session
        
        # We need to ensure the session exists in the service
        from app.models.prompt_tree import PromptTreeSession, TreeNode
        session = PromptTreeSession(id="fake_session_id", nodes=[
            TreeNode(id="fake_node", question="Q1")
        ], current_node_id="fake_node")
        app.state.tree_prompt_service.sessions["fake_session_id"] = session
        
        response = client.post("/api/prompt-helper/answer", data={"node_id": "fake_node", "answer": "A1"})
        
        assert response.status_code == 200
        assert response.json()["success"] is True

def test_save_prompt(override_auth):
    with patch("starlette.requests.Request.session", new_callable=PropertyMock) as mock_session_prop:
        mock_session = {"prompt_tree_session_id": "fake_session_id"}
        mock_session_prop.return_value = mock_session
        
        with patch("app.services.tree_prompt_service.TreePromptService.synthesize_prompt") as mock_synth:
            mock_synth.return_value = "Synthesized text"
            
            response = client.post("/api/prompt-helper/save", data={"title": "Test Title"})
            assert response.status_code == 200
            assert response.json()["success"] is True
            filename = response.json()["filename"]
            assert os.path.exists(os.path.join("prompts", filename))
            # Cleanup
            os.remove(os.path.join("prompts", filename))

def test_rewind_session(override_auth):
    with patch("starlette.requests.Request.session", new_callable=PropertyMock) as mock_session_prop:
        mock_session = {"prompt_tree_session_id": "fake_session_id"}
        mock_session_prop.return_value = mock_session
        
        from app.models.prompt_tree import PromptTreeSession, TreeNode
        session = PromptTreeSession(id="fake_session_id", nodes=[
            TreeNode(id="node1", question="Q1")
        ], current_node_id="node1")
        app.state.tree_prompt_service.sessions["fake_session_id"] = session
        
        response = client.post("/api/prompt-helper/rewind", data={"node_id": "node1"})
        assert response.status_code == 200
        assert response.json()["success"] is True

def test_unauthorized_access():
    # Dependency override not set, should use real get_user which raises 401
    response = client.get("/api/prompt-helper/session")
    assert response.status_code == 401

def test_no_session_errors(override_auth):
    with patch("starlette.requests.Request.session", new_callable=PropertyMock) as mock_session_prop:
        mock_session = {} # No session ID
        mock_session_prop.return_value = mock_session
        
        assert client.post("/api/prompt-helper/answer", data={"node_id": "x", "answer": "y"}).status_code == 400
        assert client.post("/api/prompt-helper/rewind", data={"node_id": "x"}).status_code == 400
        assert client.post("/api/prompt-helper/save", data={"title": "x"}).status_code == 400

from unittest.mock import PropertyMock