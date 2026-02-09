# Implementation Plan - Improve Auto Chat Naming

This plan focuses on enhancing the auto-generated chat titles by filtering out technical metadata like system instructions and file paths from the initial user message.

## Phase 1: Backend Logic (TDD)
- [ ] Task: Create failing unit tests for title filtering in `tests/test_title_filtering.py`.
    - [ ] Test filtering of `[SYSTEM INSTRUCTION: ... ]`.
    - [ ] Test filtering of `@path` references.
    - [ ] Test filtering of absolute and relative file paths.
    - [ ] Test fallback to "New Conversation" for empty results.
- [ ] Task: Implement filtering logic in `app/services/llm_service.py`.
    - [ ] Create a `filter_title_text(text: str) -> str` utility method.
    - [ ] Implement regex-based removal of system instructions.
    - [ ] Implement regex-based removal of file path patterns.
- [ ] Task: Integrate filtering into the chat flow.
    - [ ] Update `generate_response_stream` in `app/services/llm_service.py` to capture the first prompt of a new session.
    - [ ] Apply `filter_title_text` to the captured prompt.
    - [ ] Automatically call `update_session_title` with the cleaned string when a new session ID is first detected.
- [ ] Task: Verify backend tests pass and ensure no regressions in existing session management.
- [ ] Task: Conductor - User Manual Verification 'Backend Logic (TDD)' (Protocol in workflow.md)

## Phase 2: Final Verification & Cleanup
- [ ] Task: Run full test suite including session, tagging, and the new filtering tests.
- [ ] Task: Manual verification: Start new conversations with various combinations of system instructions and attachments.
    - [ ] Scenario 1: Only system instruction -> "New Conversation".
    - [ ] Scenario 2: System instruction + User text -> User text as title.
    - [ ] Scenario 3: User text + @file path -> User text as title.
- [ ] Task: Conductor - User Manual Verification 'Final Verification & Cleanup' (Protocol in workflow.md)
