# Implementation Plan - High Demand Retry/Stop UI

This plan covers the implementation of a user-facing "Retry/Stop" interaction when the Gemini CLI signals high demand.

## Phase 1: Research and Backend Detection
- [ ] Task: Identify the exact "High Demand" output string from Gemini CLI.
    - [ ] Sub-task: Check Gemini CLI help or simulated runs to see the message text.
- [ ] Task: Update `GeminiAgent.generate_response_stream` to detect the high demand signal.
    - [ ] Sub-task: Add detection logic in the `stdout`/`stderr` reading loop.
    - [ ] Sub-task: Yield a `{"type": "question", ...}` chunk when detected.
    - [ ] Sub-task: If detected, terminate the current CLI process to avoid hanging on `stdin`.
- [ ] Task: Conductor - User Manual Verification 'Phase 1: Research and Backend Detection' (Protocol in workflow.md)

## Phase 2: Frontend Interaction
- [ ] Task: Enhance `script.js` to handle the "Retry/Stop" question card specially.
    - [ ] Sub-task: Identify "is_retry" or similar flag in the question chunk.
    - [ ] Sub-task: Ensure the "Stop" option triggers the same logic as the global "Stop" button (`/stop` endpoint).
    - [ ] Sub-task: Ensure "Retry" sends a "Retry" message to resume the session.
- [ ] Task: Conductor - User Manual Verification 'Phase 2: Frontend Interaction' (Protocol in workflow.md)

## Phase 3: Testing and Refinement
- [ ] Task: Create a test to simulate the high demand signal and verify the question card generation.
    - [ ] Sub-task: Add a new test case in `tests/test_interactive_parsing.py`.
- [ ] Task: Verify the "Stop" action correctly interrupts the backend task.
- [ ] Task: Verify the "Retry" action correctly starts a new session attempt.
- [ ] Task: Conductor - User Manual Verification 'Phase 3: Testing and Refinement' (Protocol in workflow.md)
