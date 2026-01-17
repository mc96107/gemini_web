# Implementation Plan - Chunked Tool Output Protocol

## Phase 1: Investigation & Setup
- [ ] Task: Locate CLI Source
    - [ ] Search the current directory and subdirectories for the `gemini` CLI source code (look for `package.json` or `.js` files related to the CLI).
- [ ] Task: Baseline Test Case
    - [ ] Create a reproduction script that triggers a large tool output (e.g., searching a large directory) to confirm the failure.
- [ ] Task: Conductor - User Manual Verification 'Investigation' (Protocol in workflow.md)

## Phase 2: CLI Protocol Upgrade (Node.js)
- [ ] Task: Write Failing Test for CLI
    - [ ] If the CLI has its own test suite, add a test for large output.
- [ ] Task: Implement Chunking in CLI
    - [ ] Modify the tool execution logic to split output into 32KB chunks.
    - [ ] Emit `tool_result_start`, `tool_result_chunk`, and `tool_result_end` JSON messages.
- [ ] Task: Conductor - User Manual Verification 'CLI Upgrade' (Protocol in workflow.md)

## Phase 3: Python Backend Integration
- [ ] Task: Write Failing Integration Test
    - [ ] Create a test in `tests/` that mocks the `gemini` CLI outputting chunks and verifies `GeminiAgent` reconstructs it correctly.
- [ ] Task: Increase Python Buffer Limit
    - [ ] Update `generate_response_stream` in `llm_service.py` to increase the `StreamReader` limit to 1MB using the `_limit` hack or manual pipe connection.
- [ ] Task: Implement Chunk Accumulator
    - [ ] Update the JSON parsing loop in `generate_response_stream` to handle the new chunked message types.
- [ ] Task: Conductor - User Manual Verification 'Backend Integration' (Protocol in workflow.md)

## Phase 4: Verification & Refinement
- [ ] Task: End-to-To Stress Test
    - [ ] Run the reproduction script from Phase 1 and confirm it now passes on the Raspberry Pi.
- [ ] Task: Memory Profiling
    - [ ] Monitor RAM usage on the Pi during large transfers to ensure stability.
- [ ] Task: Conductor - User Manual Verification 'Final Verification' (Protocol in workflow.md)
