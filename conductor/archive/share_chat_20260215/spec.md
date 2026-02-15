# Specification: Share Chat Collaboration

## Overview
This track implements a multi-user collaboration feature allowing users to share active chat sessions with other registered users by username. Shared chats allow all participants to send messages and interact with tools, leveraging the underlying session storage to allow multi-user access.

## Functional Requirements
- **Sharing Trigger:** A new "Share" icon/button in the active chat header and mobile actions menu.
- **Recipient Management:** Users can share a chat with one or more recipients by typing their usernames.
- **Silent Validation:** If a target username does not exist, the sharing operation fails silently (no error message shown).
- **Collaboration Mode:** Full collaboration. Both the original owner and all recipients can read, send messages, and execute tools in the shared session.
- **UI Visibility:** Private Mode. There is no visual indicator in the chat UI that the session is shared or who else is participating.
- **Recipient Sidebar:** Shared chats automatically appear in the recipient's sidebar, sorted by last activity.
- **Metadata Inheritance:** Recipients see the same custom title, tags, and enabled tools as the original owner.
- **Access Lifecycle:** 
    - Any participant can "delete" the chat from their view.
    - Deleting a shared chat only removes access for the user who performed the deletion; it does not affect the chat or access for other participants.
    - The underlying session files are only deleted from the system when the *last* user tracking the session deletes it.

## Non-Functional Requirements
- **Security:** Ensure that only authorized users (owner or confirmed recipients) can access the chat session via the API.
- **Performance:** Sharing is a lightweight metadata operation that modifies `user_sessions.json`.

## Acceptance Criteria
- [ ] Share button exists in the chat header and mobile actions menu.
- [ ] Clicking the Share button prompts for a username.
- [ ] Entering a valid username grants that user full collaborative access by adding the session ID to their list in `user_sessions.json`.
- [ ] Entering an invalid username results in no action and no error.
- [ ] Shared chat appears in the recipient's sidebar with the correct title and tags.
- [ ] Both users can post messages to the same chat and see each other's updates.
- [ ] Deleting the chat for one user does not remove it for the other, unless it was the last user.

## Out of Scope
- Real-time "User is typing" indicators.
- Presence indicators (who is currently online/viewing).
- Explicit "Revoke" management UI (beyond personal deletion).
