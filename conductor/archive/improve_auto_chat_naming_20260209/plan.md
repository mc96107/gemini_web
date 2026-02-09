# Implementation Plan - Improve Auto Chat Naming

This plan focuses on enhancing the auto-generated chat titles by filtering out technical metadata like system instructions and file paths from the initial user message.

## Phase 1: Backend Logic (TDD)
- [x] Task: Create failing unit tests for title filtering in `tests/test_title_filtering.py`.
    - [x] Test filtering of `[SYSTEM INSTRUCTION: ... ]`.
    - [x] Test filtering of `@path` references.
    - [x] Test filtering of absolute and relative file paths.
    - [x] Test fallback to "New Conversation" for empty results.
- [x] Task: Implement filtering logic in `app/services/llm_service.py`.
    - [x] Create a `filter_title_text(text: str) -> str` utility method.
    - [x] Implement regex-based removal of system instructions.
    - [x] Implement regex-based removal of file path patterns.
- [x] Task: Integrate filtering into the chat flow.
    - [x] Update `generate_response_stream` in `app/services/llm_service.py` to capture the first prompt of a new session.
    - [x] Apply `filter_title_text` to the captured prompt.
    - [x] Automatically call `update_session_title` with the cleaned string when a new session ID is first detected.
- [x] Task: Verify backend tests pass and ensure no regressions in existing session management.
- [x] Task: Conductor - User Manual Verification 'Backend Logic (TDD)' (Protocol in workflow.md)

## Phase 2: Final Verification & Cleanup
- [x] Task: Run full test suite including session, tagging, and the new filtering tests.
- [x] Task: Manual verification: Start new conversations with various combinations of system instructions and attachments.
    - [x] Scenario 1: Only system instruction -> "New Conversation".
    - [x] Scenario 2: System instruction + User text -> User text as title.
    - [x] Scenario 3: User text + @file path -> User text as title.
- [x] Task: Conductor - User Manual Verification 'Final Verification & Cleanup' (Protocol in workflow.md)
