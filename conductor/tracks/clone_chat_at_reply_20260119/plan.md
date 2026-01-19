# Implementation Plan: Clone Chat at Reply

## Phase 1: Backend Cloning Logic [checkpoint: phase1_complete]
- [x] Task 1: Add `clone_session` method to `GeminiAgent` class in `app/services/llm_service.py`.
- [x] Task 2: Create a new API endpoint `POST /sessions/{uuid}/clone` in `app/routers/chat.py`.
- [x] Task 3: Add unit tests for session cloning logic in `tests/test_cloning.py`.

## Phase 2: Frontend UI - Clone Button [checkpoint: phase2_complete]
- [x] Task 4: Modify `app/static/script.js` to add a "Clone" button to Gemini messages.
- [x] Task 5: Implement UI feedback when a chat is cloned and auto-switch to new session.

## Phase 3: Fork Navigation & Tree View
- [~] Task 6: Implement "Fork Navigation" UI (arrows) in the message area.
- [ ] Task 7: Implement a "Tree View" for chat navigation.
- [x] Task 8: Implement synchronization for titles and tags across forks.

## Phase 4: Verification & Refinement [checkpoint: final]
- [x] Task 9: Verify mobile experience for the new UI elements.
- [x] Task 10: Final integration testing and bug fixes.
