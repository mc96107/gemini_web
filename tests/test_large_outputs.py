import pytest
import json
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from app.services.llm_service import GeminiAgent

@pytest.mark.anyio
async def test_truncate_large_tool_output():
    # Force asyncio backend for this test
    if asyncio.get_event_loop() is None:
        pytest.skip("No event loop")
        
    agent = GeminiAgent()
    
    # Mock subprocess
    mock_proc = AsyncMock()
    mock_proc.returncode = 0
    mock_proc.stdout = AsyncMock()
    mock_proc.stderr = AsyncMock()
    
    # Large tool output: 30KB
    large_output = "A" * 30000
    
    # JSON chunks from gemini CLI
    chunks = [
        json.dumps({"type": "init", "session_id": "test-session"}),
        json.dumps({"type": "tool_use", "tool_name": "test_tool", "parameters": {}}),
        json.dumps({"type": "tool_result", "output": large_output}),
        json.dumps({"type": "message", "role": "assistant", "content": "Done."}) 
    ]
    
    # Setup stdout.readline() to return these chunks
    mock_proc.stdout.readline.side_effect = [
        (c + "\n").encode() for c in chunks
    ] + [b""] # EOF
    
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
    assert "Full output available" in output

# To run this only with asyncio:
# pytest --anyio-backends=asyncio tests/test_large_outputs.py