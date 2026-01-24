# Implementation Plan - Chat History Optimization

## Phase 1: Backend Optimization (`app/services/llm_service.py`)

1.  **Update Data Structure:**
    - Modify `_load_user_data` to ensure `session_metadata` key exists for each user.
    - `session_metadata` will map `uuid` -> `{"original_title": str, "time": str}`.

2.  **Refactor `get_user_sessions`:**
    - Implement a check: `missing_metadata = [uid for uid in uuids if uid not in session_metadata]`.
    - If `missing_metadata` is empty, construct the return list directly from `session_metadata` + `custom_titles` + `session_tags`. **Skip CLI call.**
    - If `missing_metadata` is not empty (or `force_refresh` arg?), call `gemini --list-sessions`.
    - Parse CLI output.
    - **Update Cache:** For every session found in CLI output, update `session_metadata`.
    - **Garbage Collection:** Check for UUIDs in `uuids` that are NOT in the CLI output. Remove them (they were deleted externally).
    - Save `user_data`.
    - Return the list.

3.  **Update `delete_specific_session`:**
    - Ensure it removes the UUID from `session_metadata` as well.

## Phase 2: Frontend - Rename/Delete Modal (`app/templates/index.html`)

1.  **Create Modal HTML:**
    - ID: `renameSessionModal`
    - Input: `id="rename-input"`, label "Chat Title".
    - Footer Buttons:
        - Left: `<button class="btn btn-danger me-auto" id="btn-delete-session-modal">Delete Chat</button>`
        - Right: Cancel, Save (`id="btn-save-rename"`).

## Phase 3: Frontend - Logic (`app/static/script.js`)

1.  **Wire up `rename-session-btn`:**
    - Instead of `prompt`, open `renameSessionModal`.
    - Set `rename-input` value to current title.
    - Store the `currentUUID` in a data attribute or variable.

2.  **Handle Save:**
    - Call `/sessions/{uuid}/title`.
    - Update UI on success.
    - Close modal.

3.  **Handle Delete (Modal Button):**
    - `confirm("Are you sure...?")`
    - Call `/sessions/delete`.
    - Update UI (remove item).
    - Close modal.

## Phase 4: Verification
- Verify loading speed (should be instant after first load).
- Verify renaming works.
- Verify deleting works (backend and frontend).
- Verify deleted sessions disappear.
