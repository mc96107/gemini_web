# Plan - Fix Conversation Branching Point

Correct the index mismatch between the UI and raw session data to ensure the "Fork" functionality preserves the user-selected message and its preceding history.

## Phase 1: Reproduction and Diagnosis
- [x] Task: Create a reproduction script to confirm the index mismatch.
    - [x] Create `tests/reproduce_fork_mismatch.py` that generates a session file with empty messages (simulating tool calls).
    - [x] Implement a test case that attempts to "clone" the session using UI-level indices and asserts the resulting message count.
- [x] Task: Conductor - User Manual Verification 'Reproduction and Diagnosis' (Protocol in workflow.md)

## Phase 2: Backend Enhancement (Indexing)
- [x] Task: Update `LLMService.get_session_messages` to expose raw indices.
    - [x] Modify `app/services/llm_service.py` to include the original `messages` array index in each returned message object.
- [x] Task: Verify backend index exposure.
    - [x] Write a unit test in `tests/test_llm_service_indexing.py` to ensure the API now returns `raw_index` for each message.
- [x] Task: Conductor - User Manual Verification 'Backend Enhancement' (Protocol in workflow.md)

## Phase 3: Frontend Integration
- [x] Task: Update UI to store and use raw indices.
    - [x] Modify `app/static/script.js`'s `loadMessages` function to use the `raw_index` from the API when setting `messageDiv.dataset.index`.
    - [x] Ensure `handleClone` continues to pass the value from `dataset.index` to the `/clone` endpoint.
- [x] Task: Verify frontend-backend integration.
    - [x] Use the reproduction session to manually verify that clicking "Fork" on a message correctly includes that message in the new session.
- [x] Task: Conductor - User Manual Verification 'Frontend Integration' (Protocol in workflow.md)

## Phase 4: Final Verification and Cleanup
- [x] Task: Run all existing chat-related tests to ensure no regressions.
    - [x] `pytest tests/test_services.py`
    - [x] `pytest tests/test_routers.py`
- [x] Task: Conductor - User Manual Verification 'Final Verification and Cleanup' (Protocol in workflow.md)