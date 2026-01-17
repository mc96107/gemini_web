# Implementation Plan - Add a Way to Rename Chat

## User Review Required

> [!NOTE]
> We should decide if renaming happens inline in the sidebar or via a popup. Inline is generally smoother.

## Proposed Changes

### Backend
- [ ] Add a new PUT/PATCH endpoint `/api/chat/{chat_id}/title`.
- [ ] Update the `chat_service` or database layer to handle title updates.

### Frontend
- [ ] Update `app/templates/index.html` to include rename icons in the chat history list.
- [ ] Implement rename logic in `app/static/script.js` (DOM manipulation for inline edit or modal).
- [ ] Sync the new title with the backend.

## Verification Plan

### Automated Tests
- [ ] Add a test case in `tests/test_routers.py` to verify the rename endpoint.
- [ ] Verify that renaming a non-existent chat returns 404.

### Manual Verification
- [ ] Open the application.
- [ ] Find a chat in the sidebar.
- [ ] Click the rename button.
- [ ] Change the name and save.
- [ ] Refresh the page and verify the name persisted.
