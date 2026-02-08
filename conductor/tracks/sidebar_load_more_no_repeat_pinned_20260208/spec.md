# Specification: sidebar: load more chats: do not repeat pinned

## Overview
Currently, the sidebar's "Load More" functionality causes pinned chats to be repeated in the history list. This happens because the backend prepends pinned chats to every paginated response. This track aims to strictly separate pinned chats from the paginated history list on the server side to ensure they only appear once at the top of the sidebar.

## Functional Requirements
1.  **Strict Separation:** The backend `get_user_sessions` logic must be updated to ensure that pinned chats are excluded from the list of sessions returned for the paginated history.
2.  **Pinned Section:** The initial load should still provide pinned chats, but they must be clearly distinguished or returned in a way that the client can render them in a dedicated "Pinned" section.
3.  **Pagination Logic:** When requesting subsequent pages (where `offset > 0`), the server must return ONLY the requested slice of *unpinned* chats.
4.  **Pin/Unpin Behavior:**
    -   When a chat is pinned, it should be removed from the "Recent/History" list and moved to the "Pinned" section.
    -   When a chat is unpinned, it should return to its correct chronological position in the "Recent/History" list.

## Non-Functional Requirements
1.  **Lightweight API:** Minimize the amount of redundant data sent over the wire by not repeating pinned chat metadata in paginated responses.
2.  **UI Consistency:** Ensure the sidebar UI correctly handles the transition of chats between the pinned and unpinned states without requiring a full page reload.

## Acceptance Criteria
- [ ] Pinned chats appear at the top of the sidebar.
- [ ] Clicking "Load More" appends new history items without repeating any pinned chats.
- [ ] Pinning a chat moves it from the history list to the pinned section immediately.
- [ ] Unpinning a chat moves it from the pinned section back to the history list (or its chronological position).
- [ ] The "Load More" button visibility is correctly calculated based only on the count of unpinned chats.

## Out of Scope
-   Changing the visual design of the pinned/unpinned icons.
-   Adding search functionality within the pinned section specifically (unless already existing).
