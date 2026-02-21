import pytest
import os
import json
from app.services.llm_service import OpenCodeAgent


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def agent(tmp_path):
    return OpenCodeAgent(working_dir=str(tmp_path))


def test_toggle_pin(agent):
    user_id = "test_user"
    session_uuid = "12345678-1234-5678-1234-567812345678"

    # Initialize user data
    agent.user_data[user_id] = {
        "active_session": session_uuid,
        "sessions": [session_uuid],
        "session_tools": {},
        "pinned_sessions": [],
    }

    # Toggle pin ON
    assert agent.toggle_pin(user_id, session_uuid) is True
    assert session_uuid in agent.user_data[user_id]["pinned_sessions"]

    # Toggle pin OFF
    assert agent.toggle_pin(user_id, session_uuid) is False
    assert session_uuid not in agent.user_data[user_id]["pinned_sessions"]


@pytest.mark.anyio
async def test_get_user_sessions_pagination(agent, monkeypatch):
    user_id = "test_user"

    # 15 sessions total, 2 are pinned
    uuids = [f"12345678-1234-5678-1234-5678123456{i:02d}" for i in range(15)]
    pinned = [uuids[0], uuids[1]]

    agent.user_data[user_id] = {
        "active_session": uuids[14],
        "sessions": uuids,
        "session_tools": {},
        "pinned_sessions": pinned,
        "session_metadata": {
            u: {"original_title": f"Chat {i}", "time": "2026-01-15"}
            for i, u in enumerate(uuids)
        },
    }

    # Test with limit=5, offset=0
    # Expected: {"pinned": [2 items], "history": [5 items], "total_unpinned": 13}
    data = await agent.get_user_sessions(user_id, limit=5, offset=0)

    assert isinstance(data, dict)
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
    assert len(data_offset["pinned"]) == 0  # Pinned only on offset 0
    assert len(data_offset["history"]) == 5
    assert data_offset["total_unpinned"] == 13

    # Verify history chats in offset 5 are different from offset 0
    offset_history_uuids = [s["uuid"] for s in data_offset["history"]]
    for hu in history_uuids:
        assert hu not in offset_history_uuids


@pytest.mark.anyio
async def test_search_sessions(agent, monkeypatch, tmp_path):
    user_id = "test_user"
    session_uuid = "ses_12345678123456781234567812345678"

    agent.user_data[user_id] = {"sessions": [session_uuid], "pinned_sessions": []}

    # Mock --list-sessions and export
    class MockProc:
        def __init__(self, args):
            self.args = args

        async def communicate(self):
            if "export" in self.args:
                output = f"Exporting session: {session_uuid}\n" + json.dumps(
                    {
                        "messages": [
                            {
                                "info": {"role": "user"},
                                "parts": [{"type": "text", "text": "Hello world"}],
                            },
                            {
                                "info": {"role": "assistant"},
                                "parts": [
                                    {"type": "text", "text": "I found a secret key"}
                                ],
                            },
                        ]
                    }
                )
                return output.encode(), b""
            else:  # session list
                output = json.dumps(
                    [
                        {
                            "id": session_uuid,
                            "title": "My Test Chat",
                            "created": 1771684004294,
                        }
                    ]
                )
                return output.encode(), b""

    async def mock_create_subprocess_exec(*args, **kwargs):
        return MockProc(args)

    monkeypatch.setattr("asyncio.create_subprocess_exec", mock_create_subprocess_exec)

    # Search for "secret"
    results = await agent.search_sessions(user_id, "secret")
    assert len(results) == 1
    assert results[0]["uuid"] == session_uuid

    # Search for "notfound"
    results = await agent.search_sessions(user_id, "notfound")
    assert len(results) == 0
