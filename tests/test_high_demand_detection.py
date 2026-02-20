import json
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from app.services.llm_service import GeminiAgent

@pytest.mark.asyncio
async def test_detect_high_demand_in_stdout(tmp_path):
    agent = GeminiAgent(working_dir=str(tmp_path))
    user_id = "test_user"
    
    agent._create_subprocess = AsyncMock()
    mock_proc = AsyncMock()
    mock_proc.stdin = AsyncMock()
    mock_proc.stdout = AsyncMock()
    mock_proc.stderr = AsyncMock()
    mock_proc.wait = AsyncMock(return_value=0)
    mock_proc.terminate = MagicMock()
    agent._create_subprocess.return_value = mock_proc

    # Simulate "High demand. Retry?" in stdout
    # It might come as a raw line (not JSON)
    chunks = [
        b"High demand. Retry?\n",
    ]
    
    queue = asyncio.Queue()
    for c in chunks: queue.put_nowait(c)
    queue.put_nowait(b"")
    mock_proc.stdout.readline = queue.get
    mock_proc.stderr.readline = AsyncMock(return_value=b"")

    found_high_demand = False
    async for chunk in agent.generate_response_stream(user_id, "Hello"):
        if chunk.get("type") == "question" and "high demand" in chunk.get("question", "").lower():
            assert "Retry" in chunk["options"]
            assert "Stop" in chunk["options"]
            found_high_demand = True
            
    assert found_high_demand is True
    # Ensure process was terminated to avoid hanging
    mock_proc.terminate.assert_called()

@pytest.mark.asyncio
async def test_detect_high_demand_in_stderr(tmp_path):
    agent = GeminiAgent(working_dir=str(tmp_path))
    user_id = "test_user"
    
    agent._create_subprocess = AsyncMock()
    mock_proc = AsyncMock()
    mock_proc.stdin = AsyncMock()
    mock_proc.stdout = AsyncMock()
    mock_proc.stderr = AsyncMock()
    mock_proc.wait = AsyncMock(return_value=0)
    mock_proc.terminate = MagicMock()
    agent._create_subprocess.return_value = mock_proc

    # Simulate "High demand. Retry?" in stderr
    stderr_chunks = [
        b"Some other error\n",
        b"High demand. Retry?\n",
    ]
    
    stderr_queue = asyncio.Queue()
    for c in stderr_chunks: stderr_queue.put_nowait(c)
    stderr_queue.put_nowait(b"")
    mock_proc.stderr.readline = stderr_queue.get
    
    # stdout returns nothing
    mock_proc.stdout.readline = AsyncMock(return_value=b"")

    found_high_demand = False
    async for chunk in agent.generate_response_stream(user_id, "Hello"):
        if chunk.get("type") == "question" and "high demand" in chunk.get("question", "").lower():
            found_high_demand = True
            
    assert found_high_demand is True
    mock_proc.terminate.assert_called()
