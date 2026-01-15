# Implementation Plan - Sidebar Search, Pagination, and Pinned Chats

## Phase 1: Backend Data Model & APIs [checkpoint: db78350]
- [x] Task: Support Pinned Chats in `GeminiAgent`
    - [x] Update `self.user_data` structure to store a list of `pinned_sessions` for each user.
    - [x] Add `pinned` boolean to the objects returned by `get_user_sessions`.
    - [x] Create `@router.post("/sessions/{session_uuid}/pin")` to toggle pin status.
- [x] Task: Implement Paginated Session Listing
    - [x] Update `get_user_sessions` to accept `limit` and `offset` parameters.
    - [x] Ensure the logic returns pinned chats first (always), then the paginated slice of unpinned chats.
- [x] Task: Global Search Logic
    - [x] Create `@router.get("/sessions/search")` endpoint.
    - [x] Implement backend logic to scan all chat JSON files for keywords in titles, message content, and attachment names.
- [x] Task: Conductor - User Manual Verification 'Backend Data & APIs' (Protocol in workflow.md)

## Phase 2: Frontend Structure & Styling
- [ ] Task: Update Sidebar Template
    - [ ] Add search input field at the top of the `#sessions-list`.
    - [ ] Add "Load More" button at the bottom of the session list.
    - [ ] Add pin icon buttons to the session item template in `renderSessions`.
- [ ] Task: Sidebar Styling
    - [ ] Style the search bar for dark mode.
    - [ ] Style the pin icon (e.g., gold when active, subtle outline when inactive).
- [ ] Task: Conductor - User Manual Verification 'Frontend Structure' (Protocol in workflow.md)

## Phase 3: Interaction Logic
- [ ] Task: Implement Incremental Loading
    - [ ] Update `loadSessions` in `script.js` to manage `offset` and append results when "Load More" is clicked.
- [ ] Task: Live Search Implementation
    - [ ] Add a debounced event listener to the search input.
    - [ ] Implement search result rendering that overrides the standard list while a query is present.
- [ ] Task: Pinning Interaction
    - [ ] Add click handlers for the pin icon to call the new backend toggle endpoint.
    - [ ] Ensure the UI re-renders correctly to move pinned items to the top.
- [ ] Task: Conductor - User Manual Verification 'Interaction Logic' (Protocol in workflow.md)

## Phase 4: Verification & Cleanup
- [ ] Task: Performance Check
    - [ ] Verify search remains responsive with a large number of sessions.
- [ ] Task: Final Quality Gate
    - [ ] Ensure mobile responsiveness of the search and load more button.
- [ ] Task: Conductor - User Manual Verification 'Final Verification' (Protocol in workflow.md)
