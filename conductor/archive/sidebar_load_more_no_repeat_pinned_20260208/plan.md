# Implementation Plan - sidebar: load more chats: do not repeat pinned

This plan addresses the issue where pinned chats are duplicated in the sidebar when loading more history. It involves strictly separating pinned and unpinned chats on the backend and updating the frontend to render them in distinct sections.

## Phase 1: Backend Refactor (TDD) [checkpoint: e07ddcd]
- [x] Task: Create failing test for paginated session duplication in `tests/test_pinned_chats.py`. e07ddcd
- [x] Task: Update `app/services/llm_service.py`: Modify `get_user_sessions` to return a dictionary structure `{"pinned": [...], "history": [...], "total_unpinned": int}`. e07ddcd
- [x] Task: Ensure `pinned` list is only populated in the response when `offset == 0`. e07ddcd
- [x] Task: Update `app/routers/chat.py`: Adjust all routes that call `get_user_sessions` (index, /sessions) to handle the new dictionary return format. e07ddcd
- [x] Task: Update `app/services/llm_service.py`: Adjust `search_sessions` and other internal callers to handle the new format. e07ddcd
- [x] Task: Verify all backend tests pass, ensuring no regressions in session retrieval or pinning. e07ddcd
- [x] Task: Conductor - User Manual Verification 'Backend Refactor (TDD)' (Protocol in workflow.md) e07ddcd

## Phase 2: Frontend Refactor [checkpoint: 1964ac7]
- [x] Task: Update `app/templates/index.html`: Refactor the `#sessions-list` container to include two distinct sub-containers: `#pinned-sessions-list` and `#history-sessions-list`, with appropriate headers (e.g., "Pinned" and "Recent"). 1964ac7
- [x] Task: Update `app/static/script.js`: Modify `renderSessions` to accept the new dictionary format and render chats into their respective containers. 1964ac7
- [x] Task: Update `loadSessions`: Ensure that when `append=true`, only the `#history-sessions-list` is updated and the "Load More" logic uses `total_unpinned`. 1964ac7
- [x] Task: Update Pin/Unpin handlers: Ensure toggling a pin moves the session element between the two lists without a full page reload or duplication. 1964ac7
- [x] Task: Update `app/static/style.css`: Add styles for the new sidebar section headers and ensure consistent spacing. 1964ac7
- [x] Task: Conductor - User Manual Verification 'Frontend Refactor' (Protocol in workflow.md) 1964ac7

## Phase 3: Final Verification & Cleanup
- [x] Task: Run full test suite including existing pinned chat tests and new pagination tests. 5e71e9b
- [x] Task: Manual verification: Verify "Load More" behavior on desktop and mobile, ensuring pinned chats never repeat and the transition between pinned/unpinned is smooth. 5e71e9b
- [x] Task: Verify that "Pinned" chats remain at the top even after searching and clearing search. 5e71e9b
- [x] Task: Conductor - User Manual Verification 'Final Verification & Cleanup' (Protocol in workflow.md) 5e71e9b
