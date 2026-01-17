# Specification: Chunked Tool Output Protocol

## Overview
Resolve the `Separator is not found, and chunk exceed the limit` error by implementing a chunked data transfer protocol between the `gemini` CLI (Node.js) and the `GeminiAgent` (Python). This ensures the Raspberry Pi can safely handle extremely large tool outputs (for Gemini's 1M+ context window) without hitting local buffer limits.

## Functional Requirements

### 1. CLI Protocol Upgrade (Node.js)
- **Chunking Logic:** Modify the `gemini` CLI to monitor the size of tool results. 
- **Message Types:** Instead of a single `tool_result` event, the CLI will emit:
    - `tool_result_start`: Indicates a large result is coming.
    - `tool_result_chunk`: Contains a fragment of the output (e.g., max 32KB per line).
    - `tool_result_end`: Signals the completion of the transfer.
- **Backward Compatibility:** Continue to support standard `tool_result` for small outputs (<32KB).

### 2. Python Backend Update (`llm_service.py`)
- **Accumulation Buffer:** Implement a state machine in the stream reader to identify `tool_result_chunk` messages and accumulate them into a memory-efficient buffer.
- **Safety Limit:** Set a high overall limit for the total accumulated tool output (e.g., 50MB) to prevent OOM on the Raspberry Pi, while keeping individual line reads small.
- **Buffer Hack:** As a temporary measure, increase the `asyncio.StreamReader` default limit to 1MB to handle metadata-heavy lines.

## Non-Functional Requirements
- **Memory Efficiency:** Use string joining or lists for accumulation to minimize memory copies on the Pi.
- **Stability:** Ensure the system handles partial transfers or process crashes without leaving the backend in an inconsistent state.

## Acceptance Criteria
- [ ] Large tool outputs (e.g., `run_shell_command("ls -R /")`) no longer trigger the "Separator not found" exception.
- [ ] The full tool output is correctly reconstructed in the Python backend.
- [ ] The LLM receives the complete output even when it exceeds 64KB.
- [ ] No significant performance degradation on the Raspberry Pi.

## Out of Scope
- Modifying the underlying LLM's tokenization logic.
- Persistence of raw tool outputs between sessions.
