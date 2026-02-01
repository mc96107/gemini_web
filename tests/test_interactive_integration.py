import json
import pytest
import asyncio
from fastapi.testclient import TestClient
from app.main import app
from app.routers.chat import get_user
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_interactive_chat_flow_integration():
    client = TestClient(app)
    
    # 1. Mock user session
    async def override_get_user():
        return "test_user"
    app.dependency_overrides[get_user] = override_get_user
    
    # 2. Mock GeminiAgent response to return a question JSON
    # We need to mock the subprocess output
    question_json = {
        "type": "question", 
        "question": "Choose a color", 
        "options": ["Red", "Blue"], 
        "allow_multiple": False
    }
    
    # Correctly mock the streaming response from GeminiAgent
    # We patch the _create_subprocess in the actual agent instance in app.state
    agent = app.state.agent
    
    with patch.object(agent, '_create_subprocess', new_callable=AsyncMock) as mock_create:
        mock_proc = AsyncMock()
        mock_proc.stdin = AsyncMock()
        mock_proc.stdout = AsyncMock()
        mock_proc.stderr = AsyncMock()
        mock_proc.wait = AsyncMock(return_value=0)
        mock_proc.stderr.readline = AsyncMock(return_value=b"")
        
        # Simulate stdout returning a message with the JSON question
        chunks = [
            json.dumps({"type": "init", "session_id": "test-session-id"}).encode() + b"\n",
            json.dumps({"type": "message", "role": "assistant", "content": "I have a question: "}).encode() + b"\n",
            json.dumps({"type": "message", "role": "assistant", "content": json.dumps(question_json)}).encode() + b"\n",
            json.dumps({"type": "message", "role": "assistant", "content": " Please pick one."}).encode() + b"\n"
        ]
        
        queue = asyncio.Queue()
        for c in chunks: queue.put_nowait(c)
        queue.put_nowait(b"")
        mock_proc.stdout.readline = queue.get
        
        mock_create.return_value = mock_proc
        
        # 3. Call /chat endpoint
        response = client.post("/chat", data={"message": "Hello", "model": "gemini-2.5-flash"})
        assert response.status_code == 200
        
        # 4. Parse the SSE stream
        events = []
        for line in response.iter_lines():
            if line.startswith("data: "):
                data_str = line[6:]
                if data_str == "[DONE]": break
                events.append(json.loads(data_str))
        
        # 5. Verify events
        # We expect a 'question' event to be present
        question_events = [e for e in events if e.get("type") == "question"]
        assert len(question_events) == 1
        assert question_events[0]["question"] == "Choose a color"
        
        # We also expect the 'message' content to NOT contain the raw JSON
        full_text = "".join([e["content"] for e in events if e.get("type") == "message"])
        assert "I have a question:" in full_text
        assert "Please pick one." in full_text
        assert '{"type":' not in full_text
        
    del app.dependency_overrides[get_user]
