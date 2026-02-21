import pytest
import json
import asyncio
import os
from unittest.mock import MagicMock, AsyncMock, patch
from app.services.llm_service import OpenCodeAgent


@pytest.mark.anyio
async def test_truncate_large_tool_output():
    # Force asyncio backend for this test
    if asyncio.get_event_loop() is None:
        pytest.skip("No event loop")

    agent = OpenCodeAgent()

    # Mock subprocess
    mock_proc = AsyncMock()
    mock_proc.returncode = 0
    mock_proc.stdout = AsyncMock()
    mock_proc.stderr = AsyncMock()

    # Large tool output: 30KB
    large_output = "A" * 30000

    # JSON chunks from opencode CLI
    chunks = [
        json.dumps({"type": "step_start", "sessionID": "test-session"}),
        json.dumps(
            {
                "type": "tool_use",
                "sessionID": "test-session",
                "part": {
                    "type": "tool",
                    "tool": "test_tool",
                    "state": {"status": "completed", "output": large_output},
                },
            }
        ),
        json.dumps(
            {"type": "text", "sessionID": "test-session", "part": {"text": "Done."}}
        ),
    ]

    # Setup stdout.readline() to return these chunks
    mock_proc.stdout.readline.side_effect = [(c + "\n").encode() for c in chunks] + [
        b""
    ]  # EOF

    # Setup stderr.readline() to return EOF immediately
    mock_proc.stderr.readline.return_value = b""

    with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
        received_chunks = []
        async for chunk in agent.generate_response_stream("user", "prompt"):
            received_chunks.append(chunk)

    # Find the tool_result chunk
    tool_result = next(c for c in received_chunks if c.get("type") == "tool_result")

    # It should be truncated
    output = tool_result.get("output", "")
    assert len(output) < 30000
    assert "[Output truncated" in output
    assert "full_output_path" in tool_result

    full_path = tool_result["full_output_path"]
    assert full_path.startswith("/uploads/output_")

    # Verify file was actually created
    filename = full_path.split("/")[-1]
    from app.core import config

    disk_path = os.path.join(config.UPLOAD_DIR, filename)
    assert os.path.exists(disk_path)
    with open(disk_path, "r", encoding="utf-8") as f:
        assert f.read() == large_output

    # Cleanup
    os.remove(disk_path)


# To run this only with asyncio:
# pytest --anyio-backends=asyncio tests/test_large_outputs.py
