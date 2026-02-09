import pytest
import os
import json
from app.services.llm_service import GeminiAgent

@pytest.fixture
def anyio_backend():
    return 'asyncio'

@pytest.fixture
def agent(tmp_path):
    return GeminiAgent(working_dir=str(tmp_path))

@pytest.mark.anyio
async def test_get_user_sessions_new_structure(agent, monkeypatch):
    user_id = "test_user"
    
    # 15 sessions total, 2 are pinned (uuids[0] and uuids[1])
    uuids = [f"12345678-1234-5678-1234-5678123456{i:02d}" for i in range(15)]
    pinned = [uuids[0], uuids[1]]
    
    agent.user_data[user_id] = {
        "active_session": uuids[14],
        "sessions": uuids,
        "session_tools": {},
        "pinned_sessions": pinned,
        "session_metadata": {u: {"original_title": f"Chat {i}", "time": "2026-01-15"} for i, u in enumerate(uuids)}
    }
    
    # Mock subprocess call to --list-sessions (though we have metadata cached, it might still call it if missing)
    # Actually if metadata is cached it won't call it.
    
    # Test with limit=5, offset=0
    # Expected: {"pinned": [2 items], "history": [5 items], "total_unpinned": 13}
    data = await agent.get_user_sessions(user_id, limit=5, offset=0)
    
    assert isinstance(data, dict)
    assert "pinned" in data
    assert "history" in data
    assert "total_unpinned" in data
    
    assert len(data["pinned"]) == 2
    assert len(data["history"]) == 5
    assert data["total_unpinned"] == 13
    
    # Verify pinned chats are correct
    pinned_uuids = [s["uuid"] for s in data["pinned"]]
    assert uuids[0] in pinned_uuids
    assert uuids[1] in pinned_uuids
    
    # Verify history chats do NOT include pinned ones
    history_uuids = [s["uuid"] for s in data["history"]]
    for pu in pinned_uuids:
        assert pu not in history_uuids

    # Test offset=5
    data_offset = await agent.get_user_sessions(user_id, limit=5, offset=5)
    assert len(data_offset["pinned"]) == 0 # Pinned only on offset 0
    assert len(data_offset["history"]) == 5
    assert data_offset["total_unpinned"] == 13
    
    # Verify history chats in offset 5 are different from offset 0
    offset_history_uuids = [s["uuid"] for s in data_offset["history"]]
    for hu in history_uuids:
        assert hu not in offset_history_uuids
