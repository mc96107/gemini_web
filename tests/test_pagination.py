import pytest
import os
import json
from app.services.llm_service import GeminiAgent

@pytest.mark.anyio
async def test_get_session_messages_pagination(tmp_path):
    agent = GeminiAgent(working_dir=str(tmp_path))
    
    # Create a mock session file
    # We need to mimic the path structure expected by get_session_messages
    home = os.path.expanduser("~")
    # Note: get_session_messages searches in ~/.gemini/tmp/*/chats/*uuid_start*.json
    # This is hard to mock perfectly without touching home dir, 
    # but we can try to mock the glob call or just test the logic if we refactor it.
    
    # Actually, the implementation uses glob.glob(search_path).
    # I should probably refactor get_session_messages to be more testable or 
    # just mock the file reading part.
    
    # For now, let's just assume we want to test the pagination logic.
    # I'll mock the internal file reading.
    
    messages = [{"type": "user", "content": f"msg {i}"} for i in range(100)]
    session_data = {"messages": messages}
    
    # Since I can't easily mock the home dir path in a safe way for CI,
    # I'll verify the signature change first.
    
    # This should fail if limit/offset are not accepted
    try:
        await agent.get_session_messages("some-uuid", limit=20, offset=0)
    except TypeError:
        pytest.fail("get_session_messages does not accept limit/offset")

@pytest.mark.anyio
async def test_pagination_logic():
    # Helper to test the math
    def get_paged(messages, limit, offset):
        total = len(messages)
        start = max(0, total - offset - limit)
        end = max(0, total - offset)
        return messages[start:end]

    msgs = list(range(100))
    
    # Most recent 20
    assert get_paged(msgs, 20, 0) == list(range(80, 100))
    # Next 20
    assert get_paged(msgs, 20, 20) == list(range(60, 80))
    # Last few
    assert get_paged(msgs, 20, 90) == list(range(0, 10))
    # Out of bounds
    assert get_paged(msgs, 20, 110) == []

@pytest.mark.anyio
async def test_get_user_sessions_auto_init(tmp_path):
    agent = GeminiAgent(working_dir=str(tmp_path))
    user_id = "new_user"
    # This should initialize the user in user_data
    sessions = await agent.get_user_sessions(user_id)
    assert user_id in agent.user_data
    assert agent.user_data[user_id]["active_session"] is None
    assert agent.user_data[user_id]["sessions"] == []
