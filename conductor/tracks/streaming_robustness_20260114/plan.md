# Implementation Plan - Streaming Robustness

## Phase 1: Backend Improvements
- [x] Task: Implement SSE Heartbeats
- [x] Task: Harden `llm_service.py`
- [x] Task: Fix Subprocess Deadlock and Session Capture

## Phase 2: Frontend Refinement
- [~] Task: Update `script.js` Reader
    - [x] Improve the `try-catch` block in `processStream` to distinguish between intentional closures and actual network failures.
    - [x] Ensure partial buffers are handled if the stream ends unexpectedly. (Done via heartbeats and skip logic)

## Phase 3: Verification
- [ ] Task: Simulate Long Responses
    - [ ] Test with a prompt that requires heavy thinking to verify keep-alives prevent timeouts.
- [ ] Task: Conductor - User Manual Verification 'Streaming Robustness' (Protocol in workflow.md)
