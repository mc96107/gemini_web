# Specification - Fix: New Chat Sidebar Update

## Overview
Currently, when a user starts a new conversation and sends the first message, the sidebar history is not updated to reflect the newly created session. The user must manually reload the page to see the new chat in the history. The system should maintain the current URL while updating the sidebar.

## Functional Requirements
- **Sidebar Refresh:** The sidebar chat history must automatically update to include the new session title as soon as the session is established on the backend.
- **Maintain URL:** The browser URL should remain unchanged during this transition, consistent with the project's current navigation model.
- **State Consistency:** The frontend should correctly transition from a "new chat" state to a "specific session" state internally without a full page reload.

## Non-Functional Requirements
- **Responsiveness:** The sidebar update should happen immediately after the first successful response from the backend starts or completes.
- **Robustness:** Ensure that multiple rapid first messages don't create duplicate entries or race conditions in the sidebar.

## Acceptance Criteria
- [ ] Send first message in a new chat.
- [ ] Verify the browser URL remains consistent (no `session_id` added to the path/query).
- [ ] Verify the new chat title appears at the top of the sidebar history without a manual reload.
- [ ] Verify that the new chat in the sidebar is correctly linked to the active session.

## Out of Scope
- Adding session IDs to the URL.
- Redesigning the sidebar or chat history logic.