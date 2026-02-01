import json
import pytest
import asyncio
import re
from app.services.llm_service import GeminiAgent

@pytest.mark.asyncio
async def test_detect_question_in_message(tmp_path):
    agent = GeminiAgent(working_dir=str(tmp_path))
    user_id = "test_user"
    
    # Mock data to simulate stream
    question_json = {"type": "question", "question": "What is your name?", "options": ["Alice", "Bob"], "allow_multiple": False}
    
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

@pytest.mark.asyncio
async def test_mixed_stream_parsing(tmp_path):
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

    # Message followed by question followed by more message
    chunks = [
        json.dumps({"type": "message", "role": "assistant", "content": "Here is a "}).encode(),
        json.dumps({"type": "message", "role": "assistant", "content": 'question: {"type": "question", "question": "Blue?"}'}).encode(),
        json.dumps({"type": "message", "role": "assistant", "content": " Hope you like it."}).encode(),
    ]
    
    queue = asyncio.Queue()
    for c in chunks: queue.put_nowait(c)
    queue.put_nowait(b"")
    mock_proc.stdout.readline = queue.get

    events = []
    async for chunk in agent.generate_response_stream(user_id, "Hello"):
        events.append(chunk)
    
    message_content = "".join([e["content"] for e in events if e["type"] == "message"])
    assert "Here is a question:  Hope you like it." in message_content
    
    questions = [e for e in events if e["type"] == "question"]
    assert len(questions) == 1
    assert questions[0]["question"] == "Blue?"

@pytest.mark.asyncio
async def test_no_partial_json_leakage(tmp_path):
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

    # Partial JSON across chunks
    chunks = [
        json.dumps({"type": "message", "role": "assistant", "content": 'Check this: {"type": "'}).encode(),
        json.dumps({"type": "message", "role": "assistant", "content": 'question", "question": "Ok?"}'}).encode(),
    ]
    
    queue = asyncio.Queue()
    for c in chunks: queue.put_nowait(c)
    queue.put_nowait(b"")
    mock_proc.stdout.readline = queue.get

    events = []
    async for chunk in agent.generate_response_stream(user_id, "Hello"):
        events.append(chunk)
    
    message_content = "".join([e["content"] for e in events if e["type"] == "message"])
    assert '{"type":' not in message_content
    assert 'question"' not in message_content
    assert "Check this:" in message_content

@pytest.mark.asyncio
async def test_non_question_json_transparency(tmp_path):
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

    # JSON that is NOT a question (e.g. code example)
    code_json = '{"name": "test", "value": 123}'
    chunks = [
        json.dumps({"type": "message", "role": "assistant", "content": f"Here is some code: {code_json}"}).encode(),
    ]
    
    queue = asyncio.Queue()
    for c in chunks: queue.put_nowait(c)
    queue.put_nowait(b"")
    mock_proc.stdout.readline = queue.get

    events = []
    async for chunk in agent.generate_response_stream(user_id, "Hello"):
        events.append(chunk)
    
        message_content = "".join([e["content"] for e in events if e["type"] == "message"])
    
        assert "Here is some code:" in message_content
    
        assert code_json in message_content
    
    
    
    @pytest.mark.asyncio
    
    async def test_greek_language_support(tmp_path):
    
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
    
    
    
        # Question in Greek
    
        # "Ποιο είναι το αγαπημένο σας χρώμα;" (What is your favorite color?)
    
        question_json = {
    
            "type": "question", 
    
            "question": "Ποιο είναι το αγαπημένο σας χρώμα;", 
    
            "options": ["Κόκκινο", "Μπλε", "Πράσινο"], 
    
            "allow_multiple": False
    
        }
    
        
    
        chunks = [
    
            json.dumps({"type": "message", "role": "assistant", "content": "Ορίστε μια ερώτηση: "}).encode(),
    
            json.dumps({"type": "message", "role": "assistant", "content": json.dumps(question_json)}).encode(),
    
        ]
    
        
    
        queue = asyncio.Queue()
    
        for c in chunks: queue.put_nowait(c)
    
        queue.put_nowait(b"")
    
        mock_proc.stdout.readline = queue.get
    
    
    
        events = []
    
        async for chunk in agent.generate_response_stream(user_id, "Γεια σου"):
    
            events.append(chunk)
    
        
    
        questions = [e for e in events if e["type"] == "question"]
    
        assert len(questions) == 1
    
        assert questions[0]["question"] == "Ποιο είναι το αγαπημένο σας χρώμα;"
    
        assert "Μπλε" in questions[0]["options"]
    
        
    
        message_content = "".join([e["content"] for e in events if e["type"] == "message"])
    
        assert "Ορίστε μια ερώτηση:" in message_content
    
        assert "type" not in message_content # Ensure JSON didn't leak
    
    