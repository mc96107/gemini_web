# Specification: Sidebar Search, Pagination, and Pinned Chats

## Overview
Enhance the chat sidebar by limiting the initial load of session titles to the 10 most recent conversations and introducing a "Load More" mechanism. Implement a global, live search feature across titles, text, and attachments. Additionally, add a "Pin" feature to keep important conversations at the top of the history regardless of pagination or recency.

## Functional Requirements

### 1. Sidebar Pagination
- **Initial Limit:** On page load, the session list displays the 10 most recently updated *unpinned* sessions.
- **Load More Button:** A "Load More" button appears at the bottom if more sessions are available.
- **Incremental Loading:** Clicking "Load More" fetches and appends the next 10 sessions.

### 2. Pinned Chats
- **Pinning Action:** Add a pin/unpin icon button to each session item in the sidebar.
- **Persistent Visibility:** Pinned chats are always shown at the very top of the sidebar, above the recent/paginated list.
- **Always Loaded:** Pinned chats are excluded from the 10-session pagination limit (they don't "count" towards the 10).
- **Persistence:** Pin status must be saved to the backend (e.g., in `user_sessions.json`).

### 3. Global Live Search
- **Search Input:** Add a persistent search bar at the top of the history sidebar.
- **Real-Time Filtering:** Results update as the user types (with debouncing).
- **Global Scope:** Search queries the entire historical record (titles, message text, attachment filenames).
- **Search Logic:** 
    - When searching, the pagination and "Pinned" sorting are temporarily overridden by search results.
    - Clearing the search restores the pinned-at-top and paginated view.

## Non-Functional Requirements
- **Performance:** Efficient file-system scanning for search keywords.
- **UX:** Clear visual distinction between pinned and unpinned chats.

## Acceptance Criteria
- [ ] Sidebar shows pinned chats at the top, followed by the latest 10 unpinned sessions.
- [ ] Clicking the Pin icon correctly toggles the chat's pinned status and updates the backend.
- [ ] "Load More" appends the next set of unpinned sessions.
- [ ] Global search correctly finds sessions based on content, title, or attachments.
- [ ] Clearing search returns to the standard pinned + paginated view.

## Out of Scope
- Reordering pinned chats (they remain sorted by most recent within the pinned section).
- Searching specifically *within* pinned chats only.
