# Implementation Plan - Add a Way to Rename Chat

## User Review Required

> [!NOTE]
> We should decide if renaming happens inline in the sidebar or via a popup. Inline is generally smoother.
> UPDATE: Implemented via a simple `prompt()` for now, which is effective and simple.

## Proposed Changes

### Backend
- [x] Add a new PUT/PATCH endpoint `/sessions/{session_uuid}/title`. [3d49b1d]
- [x] Update the `chat_service` or database layer to handle title updates. [3d49b1d]

### Frontend
- [x] Update `app/templates/index.html` to include rename icons in the chat history list. [3d49b1d]
- [x] Implement rename logic in `app/static/script.js` (DOM manipulation for inline edit or modal). [3d49b1d]
- [x] Sync the new title with the backend. [3d49b1d]

## Verification Plan

### Automated Tests
- [x] Add a test case in `tests/test_routers.py` (actually `tests/test_rename_chat.py`) to verify the rename endpoint. [3d49b1d]
- [x] Verify that renaming a non-existent chat returns 404. [3d49b1d]

### Manual Verification
- [ ] Open the application.
- [ ] Find a chat in the sidebar.
- [ ] Click the rename button.
- [ ] Change the name and save.
- [ ] Refresh the page and verify the name persisted.