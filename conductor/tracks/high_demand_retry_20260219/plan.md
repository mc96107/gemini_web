# Implementation Plan - High Demand Retry/Stop UI

This plan covers the implementation of a user-facing "Retry/Stop" interaction when the Gemini CLI signals high demand.

## Phase 1: Research and Backend Detection [checkpoint: 7e7fa96]
- [x] Task: Identify the exact "High Demand" output string from Gemini CLI. d5a14f9
    - [x] Sub-task: Check Gemini CLI help or simulated runs to see the message text.
- [x] Task: Update `GeminiAgent.generate_response_stream` to detect the high demand signal. d5a14f9
    - [x] Sub-task: Add detection logic in the `stdout`/`stderr` reading loop.
    - [x] Sub-task: Yield a `{"type": "question", ...}` chunk when detected.
    - [x] Sub-task: If detected, terminate the current CLI process to avoid hanging on `stdin`.
- [x] Task: Conductor - User Manual Verification 'Phase 1: Research and Backend Detection' (Protocol in workflow.md) 7e7fa96

## Phase 2: Frontend Interaction [checkpoint: 0f2a0b0]
- [x] Task: Enhance `script.js` to handle the "Retry/Stop" question card specially. 0f2a0b0
    - [x] Sub-task: Identify "is_retry" or similar flag in the question chunk.
    - [x] Sub-task: Ensure the "Stop" option triggers the same logic as the global "Stop" button (`/stop` endpoint).
    - [x] Sub-task: Ensure "Retry" sends a "Retry" message to resume the session.
- [x] Task: Conductor - User Manual Verification 'Phase 2: Frontend Interaction' (Protocol in workflow.md) 0f2a0b0

## Phase 3: Testing and Refinement
- [~] Task: Create a test to simulate the high demand signal and verify the question card generation.
    - [ ] Sub-task: Add a new test case in `tests/test_interactive_parsing.py`.
- [ ] Task: Verify the "Stop" action correctly interrupts the backend task.
- [ ] Task: Verify the "Retry" action correctly starts a new session attempt.
- [ ] Task: Conductor - User Manual Verification 'Phase 3: Testing and Refinement' (Protocol in workflow.md)
