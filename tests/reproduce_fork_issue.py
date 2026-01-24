import pytest
import os
import json
from app.services.llm_service import GeminiAgent

@pytest.mark.asyncio
async def test_clone_session_inheritance(tmp_path):
    # Setup agent with temp working directory
    agent = GeminiAgent(working_dir=str(tmp_path))
    user_id = "test_user"
    
    # 1. Create a dummy session with tools and tags
    session_uuid = "parent-uuid"
    agent.user_data[user_id] = {
        "active_session": session_uuid,
        "sessions": [session_uuid],
        "session_tools": {session_uuid: ["tool1", "tool2"]},
        "session_tags": {session_uuid: ["tag1", "tag2"]},
        "custom_titles": {session_uuid: "Parent Title"}
    }
    agent._save_user_data()

    # 2. Mock a chat JSON file so clone_session doesn't fail on message truncation
    # GeminiAgent looks in ~/.gemini/tmp/*/chats/*.json
    # This is hard to mock easily without changing the agent or mocking glob/open
    # But wait, clone_session has a branch for message_index == -1 which doesn't touch files.
    
    # Test message_index == -1 (Pending Fork)
    new_uuid_pending = await agent.clone_session(user_id, session_uuid, -1)
    assert new_uuid_pending == "pending"
    
    pending_fork = agent.user_data[user_id].get("pending_fork")
    assert pending_fork is not None
    assert pending_fork["parent"] == session_uuid
    assert pending_fork["tags"] == ["tag1", "tag2"]
    # THIS SHOULD FAIL (Red phase):
    assert "tools" in pending_fork, "Tools should be in pending_fork"
    assert pending_fork["tools"] == ["tool1", "tool2"]

if __name__ == "__main__":
    # Minimal manual run if needed
    import sys
    from pathlib import Path
    
    # Add project root to path
    sys.path.append(str(Path(__file__).parent.parent))
    
    try:
        from app.services.llm_service import GeminiAgent
        # We can't easily run pytest from here without it being installed
        # but we can call the function directly
        class MockTmpPath:
            def __init__(self, p): self.p = p
            def __str__(self): return str(self.p)
            def joinpath(self, *args): return self.p.joinpath(*args)
        
        import tempfile
        import asyncio
        with tempfile.TemporaryDirectory() as tmpdir:
            asyncio.run(test_clone_session_inheritance(Path(tmpdir)))
            print("Test passed unexpectedly!")
    except AssertionError as e:
        print(f"Test failed as expected: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()
