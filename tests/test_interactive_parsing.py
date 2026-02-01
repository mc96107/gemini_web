import json
import pytest
import asyncio
from app.services.llm_service import GeminiAgent

@pytest.mark.asyncio
async def test_detect_question_in_message(tmp_path):
    agent = GeminiAgent(working_dir=str(tmp_path))
    user_id = "test_user"
    
    # Mock data to simulate stream
    question_json = {"type": "question", "question": "What is your name?", "options": ["Alice", "Bob"], "allow_multiple": False}
    msg_content = f"Sure, I can help. {json.dumps(question_json)} Let me know."
    
    # We want to see if generate_response_stream can extract this
    from unittest.mock import AsyncMock
    agent._create_subprocess = AsyncMock()
    mock_proc = AsyncMock()
    mock_proc.stdin = AsyncMock()
    mock_proc.stdout = AsyncMock()
    mock_proc.stderr = AsyncMock()
    mock_proc.wait = AsyncMock(return_value=0)
    mock_proc.stderr.readline = AsyncMock(return_value=b"")
    agent._create_subprocess.return_value = mock_proc

    # Simulate a 'message' chunk containing the JSON
    chunks = [
        json.dumps({"type": "message", "role": "assistant", "content": "Sure, I can help. "}).encode(),
        json.dumps({"type": "message", "role": "assistant", "content": json.dumps(question_json)}).encode(),
        json.dumps({"type": "message", "role": "assistant", "content": " Let me know."}).encode()
    ]
    
    async def side_effect():
        for c in chunks:
            yield c
        yield b""

    # Mock readline to return our chunks
    queue = asyncio.Queue()
    for c in chunks: queue.put_nowait(c)
    queue.put_nowait(b"")
    mock_proc.stdout.readline = queue.get

    found_question = False
    async for chunk in agent.generate_response_stream(user_id, "Hello"):
        if chunk.get("type") == "question":
            assert chunk["question"] == "What is your name?"
            assert chunk["options"] == ["Alice", "Bob"]
            found_question = True
            
    assert found_question is True

@pytest.mark.asyncio
async def test_detect_fragmented_question(tmp_path):
    agent = GeminiAgent(working_dir=str(tmp_path))
    user_id = "test_user"
    
    from unittest.mock import AsyncMock
    agent._create_subprocess = AsyncMock()
    mock_proc = AsyncMock()
    mock_proc.stdin = AsyncMock()
    mock_proc.stdout = AsyncMock()
    mock_proc.stderr = AsyncMock()
    mock_proc.wait = AsyncMock(return_value=0)
    mock_proc.stderr.readline = AsyncMock(return_value=b"")
    agent._create_subprocess.return_value = mock_proc

    # Fragment the JSON across multiple message chunks
    chunks = [
        json.dumps({"type": "message", "role": "assistant", "content": '{"type": "ques'}).encode(),
        json.dumps({"type": "message", "role": "assistant", "content": 'tion", "question": "Are you '}).encode(),
        json.dumps({"type": "message", "role": "assistant", "content": 'sure?", "options": ["Yes", "No"], "allow_multiple": false}'}).encode(),
    ]
    
    queue = asyncio.Queue()
    for c in chunks: queue.put_nowait(c)
    queue.put_nowait(b"")
    mock_proc.stdout.readline = queue.get

    found_question = False
    async for chunk in agent.generate_response_stream(user_id, "Hello"):
        if chunk.get("type") == "question":
            assert chunk["question"] == "Are you sure?"
            found_question = True
            
    assert found_question is True
