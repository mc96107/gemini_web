# Implementation Plan: Share Chat Collaboration

This plan details the steps to implement a collaborative chat sharing feature by directly modifying `user_sessions.json` to allow multi-user access to the same Gemini CLI session.

## Phase 1: Backend Logic & API
Implement the core logic for sharing and safe deletion in the `GeminiAgent` service and expose it via API.

- [x] Task: Implement `GeminiAgent.share_session(user_id, session_uuid, target_username)` in `app/services/llm_service.py`. 28966c2
    - [ ] Verify `user_id` has access to `session_uuid`.
    - [ ] Verify `target_username` exists via `UserManager`.
    - [ ] Add `session_uuid` to `target_username`'s session list in `user_data`.
    - [ ] Copy `custom_titles`, `session_tags`, `session_metadata`, and `session_tools` to the target user.
    - [ ] Save `user_sessions.json`.
- [x] Task: Update `GeminiAgent.delete_specific_session` in `app/services/llm_service.py`. 46e8464
    - [ ] Modify the deletion logic to check if *any other user* in `user_data` still has the `target_uuid` in their `sessions` list.
    - [ ] Only call `gemini-cli --delete-session` if no other users are tracking it.
    - [ ] Always remove the session from the current user's `user_data`.
- [x] Task: Add the `/api/sessions/{session_uuid}/share` POST endpoint in `app/routers/chat.py`. 4a76a4d
    - [ ] Authenticate user and verify session ownership.
    - [ ] Call `agent.share_session`.
- [x] Task: Conductor - User Manual Verification 'Phase 1: Backend Logic & API' (Protocol in workflow.md) f25110e

## Phase 2: Frontend Implementation
Add the UI components to trigger the sharing flow.

- [ ] Task: Update `app/templates/index.html` to include the Share button in the header and mobile actions sidebar.
- [ ] Task: Implement `shareSession(uuid)` in `app/static/script.js`.
    - [ ] Show a `prompt()` to get the username.
    - [ ] Call the new share API endpoint.
    - [ ] Show a toast notification upon success (or silent completion).
- [ ] Task: Bind the Share button click events to `shareSession`.
- [ ] Task: Conductor - User Manual Verification 'Phase 2: Frontend Implementation' (Protocol in workflow.md)

## Phase 3: Verification
Ensure the multi-user collaboration and safe deletion work as expected.

- [ ] Task: Verify that sharing a chat with a valid user makes it appear in their sidebar.
- [ ] Task: Verify that both users can send messages and see the updated history.
- [ ] Task: Verify that deleting the chat as one user doesn't remove it for the other.
- [ ] Task: Verify that the last user deleting the chat correctly triggers the CLI deletion.
- [ ] Task: Conductor - User Manual Verification 'Phase 3: Verification' (Protocol in workflow.md)
