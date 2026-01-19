# Specification: Chat History Optimization & Management

## Goal
Improve the performance of chat history loading and provide better chat management tools (renaming and deletion).

## Requirements

### 1. Performance Optimization
- **Caching:** Cache session metadata (original title, timestamp) in `user_sessions.json`.
- **Lazy Loading:** `get_user_sessions` should prefer cached data. Only invoke the Gemini CLI (`--list-sessions`) if metadata is missing for tracked sessions or if explicitly requested (optional).
- **Stale Data Handling:** If a session is deleted externally, it might remain in the cache until a sync occurs. This is acceptable for performance, but the system should handle 404s gracefully.

### 2. Chat Deletion
- **UI:** Add a "Delete Chat" button within the "Rename Chat" dialog.
- **Style:** The delete button should be styled as "Danger" (red).
- **Behavior:**
  - Clicking "Delete" should prompt for confirmation.
  - Upon confirmation, trigger the backend deletion.
  - Remove the chat from the UI immediately.

### 3. Backend Logic
- **Sync:** When the CLI is called to list sessions, update the `user_sessions.json` cache with the latest titles and timestamps.
- **Cleanup:** If a session in `user_sessions.json` is not returned by the CLI (during a sync), remove it from `user_sessions.json`.
- **Delete Endpoint:** Ensure the delete endpoint removes the session from both the Gemini CLI backend (`--delete-session`) and the local `user_sessions.json` metadata.

## User Experience
- Users should see their chat history instantly without waiting for the CLI command.
- Renaming a chat should be done via a proper modal, not a system `prompt()`.
- Users can easily delete old or empty chats.
