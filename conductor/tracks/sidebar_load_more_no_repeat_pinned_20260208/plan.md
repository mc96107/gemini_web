# Implementation Plan - sidebar: load more chats: do not repeat pinned

This plan addresses the issue where pinned chats are duplicated in the sidebar when loading more history. It involves strictly separating pinned and unpinned chats on the backend and updating the frontend to render them in distinct sections.

## Phase 1: Backend Refactor (TDD)
- [ ] Task: Create failing test for paginated session duplication in `tests/test_pinned_chats.py`.
- [ ] Task: Update `app/services/llm_service.py`: Modify `get_user_sessions` to return a dictionary structure `{"pinned": [...], "history": [...], "total_unpinned": int}`.
- [ ] Task: Ensure `pinned` list is only populated in the response when `offset == 0`.
- [ ] Task: Update `app/routers/chat.py`: Adjust all routes that call `get_user_sessions` (index, /sessions) to handle the new dictionary return format.
- [ ] Task: Update `app/services/llm_service.py`: Adjust `search_sessions` and other internal callers to handle the new format.
- [ ] Task: Verify all backend tests pass, ensuring no regressions in session retrieval or pinning.
- [ ] Task: Conductor - User Manual Verification 'Backend Refactor (TDD)' (Protocol in workflow.md)

## Phase 2: Frontend Refactor
- [ ] Task: Update `app/templates/index.html`: Refactor the `#sessions-list` container to include two distinct sub-containers: `#pinned-sessions-list` and `#history-sessions-list`, with appropriate headers (e.g., "Pinned" and "Recent").
- [ ] Task: Update `app/static/script.js`: Modify `renderSessions` to accept the new dictionary format and render chats into their respective containers.
- [ ] Task: Update `loadSessions`: Ensure that when `append=true`, only the `#history-sessions-list` is updated and the "Load More" logic uses `total_unpinned`.
- [ ] Task: Update Pin/Unpin handlers: Ensure toggling a pin moves the session element between the two lists without a full page reload or duplication.
- [ ] Task: Update `app/static/style.css`: Add styles for the new sidebar section headers and ensure consistent spacing.
- [ ] Task: Conductor - User Manual Verification 'Frontend Refactor' (Protocol in workflow.md)

## Phase 3: Final Verification & Cleanup
- [ ] Task: Run full test suite including existing pinned chat tests and new pagination tests.
- [ ] Task: Manual verification: Verify "Load More" behavior on desktop and mobile, ensuring pinned chats never repeat and the transition between pinned/unpinned is smooth.
- [ ] Task: Verify that "Pinned" chats remain at the top even after searching and clearing search.
- [ ] Task: Conductor - User Manual Verification 'Final Verification & Cleanup' (Protocol in workflow.md)
