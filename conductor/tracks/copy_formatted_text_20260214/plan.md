# Implementation Plan: Copy Formatted Text to Clipboard

This plan outlines the steps to add a "Copy Formatted Text" toggle to user settings and implement the corresponding logic to copy rich text or markdown to the clipboard.

## Phase 1: Infrastructure & Settings UI [checkpoint: 9a6645f]

Implement the persistence of the new setting and the UI toggle in the settings modal.

- [x] Task: Update `GeminiAgent` to support `copy_formatted` setting. 1ae50d1
    - Modify `GeminiAgent._load_user_data` to ensure `copy_formatted` is initialized for existing sessions.
    - Update `get_user_settings` and `update_user_settings` default values.
- [x] Task: Add "Copy Formatted Text" toggle to the Security Settings modal. 147db42
    - Edit `app/templates/index.html` to add the checkbox.
- [x] Task: Sync `copy_formatted` setting with backend. a09ce2f
    - Update `app/static/script.js` to load the setting into `window.USER_SETTINGS` and handle the toggle's `change` event to perform a `fetch('/settings', ...)` POST request.
- [x] Task: Write tests for user settings persistence. 1ae50d1
    - Update `tests/test_user_settings.py` to include checks for `copy_formatted`.
- [x] Task: Conductor - User Manual Verification 'Phase 1: Infrastructure & Settings UI' (Protocol in workflow.md) 9a6645f

## Phase 2: Enhanced Copy Logic

Implement the conditional logic to copy either raw markdown or formatted rich text.

- [x] Task: Implement Rich Text Copying logic in `script.js`. bc676c6
    - Modify the `copyBtn.onclick` handler in `createMessageDiv` and message display logic.
    - If `copy_formatted` is ON, use `ClipboardItem` to write both `text/html` (from the rendered message bubble) and `text/plain` (raw markdown).
    - Ensure code block copy buttons are not affected (or handle them consistently if required).
- [ ] Task: Add frontend unit tests for copy logic.
    - Update `tests/attachment_manager.test.js` or create a new frontend test to mock the clipboard API and verify the correct blobs are created based on settings.
- [ ] Task: Conductor - User Manual Verification 'Phase 2: Enhanced Copy Logic' (Protocol in workflow.md)

## Phase 3: Final Integration & Verification

- [ ] Task: Verify cross-browser compatibility for `ClipboardItem` (especially on Termux/Android browsers).
- [ ] Task: Run full project test suite.
- [ ] Task: Conductor - User Manual Verification 'Phase 3: Final Integration & Verification' (Protocol in workflow.md)
