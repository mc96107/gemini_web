# Specification: Auto-Restore Last Active Session

## Overview
Improve the user experience by automatically restoring the last active chat session immediately upon logging in or reloading the application. If no previous session exists, a new one will be created automatically.

## Functional Requirements
- **Automatic Load:** The application must identify the `active_session` for the logged-in user and load its messages immediately on page load, without requiring the user to open the sidebar.
- **Lazy Loading/Pagination (B):**
    - The backend `/sessions/{uuid}/messages` endpoint should be updated to support pagination (e.g., via `limit` and `offset` parameters).
    - The UI should initially load the most recent 20 messages.
    - A "Load More" button or infinite scroll mechanism should be added to fetch older history.
- **Session Creation (A):** If the user has no sessions, the system must automatically call the "New Session" logic so the user lands in a fresh, ready-to-use chat.
- **Visual Feedback:**
    - **Toast Notification (A):** Display a brief Bootstrap Toast informing the user that their last session has been restored.
    - **Auto-Scroll (C):** Ensure the chat container scrolls to the bottom after history is loaded so the user sees the most recent context.

## Non-Functional Requirements
- **Performance:** Pagination is critical to ensure that users with hundreds of messages do not experience slow load times or browser crashes.
- **UI Consistency:** Use standard Bootstrap 5 Toasts for notifications.

## Acceptance Criteria
- [ ] Upon login, the chat area is automatically populated with the last active session's messages.
- [ ] If no session exists, a new session is created and the UI is ready for input.
- [ ] A toast notification appears saying "Resumed last session".
- [ ] Only the most recent 20 messages are loaded initially, with a way to load more.
- [ ] The chat automatically scrolls to the latest message on load.

## Out of Scope
- Intelligent "summarization" of old history.
- Multi-device sync beyond what is already supported by the backend JSON storage.
