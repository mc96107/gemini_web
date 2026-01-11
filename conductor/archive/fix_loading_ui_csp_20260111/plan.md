# Implementation Plan - Fix Session Loading & CSP

## Phase 1: CSP and UI Fixes
- [x] Task: Update CSP in `app/main.py` 8a05af8
    - [x] Update `SecurityHeadersMiddleware` to allow `connect-src` to `cdn.jsdelivr.net`.
- [x] Task: Fix UI Loading Hang in `app/static/script.js` 30bcc7f
    - [x] Locate the session switching logic (where "Loading conversation..." is injected).
    - [x] Ensure `loadMessages` properly handles the `chatContainer` content clearing.
    - [x] Add a safety check in `loadMessages` to remove any existing "Loading conversation..." message if it's the first page (`offset === 0`).
- [x] Task: Fix Session Retrieval Logic in `app/services/llm_service.py` 2e75236
    - [x] Direct the glob search to the project-specific temporary directory to avoid loading sessions from other contexts.
- [x] Task: Improve Session Loading Robustness in `app/services/llm_service.py` baf46a9
    - [x] Add explicit error handling and more detailed logging to `get_session_messages` to prevent silent failures when parsing session files.
- [x] Task: Conductor - User Manual Verification 'CSP and UI Fixes' (Protocol in workflow.md) baf46a9

## Phase 2: Verification
- [x] Task: Verify CSP Fix baf46a9
    - [x] Refresh the page and confirm the console no longer shows `connect-src` violations for CDN resources.
- [x] Task: Verify Session Switching baf46a9
    - [x] Switch to a session with messages and confirm it loads correctly.
    - [x] Switch to a session with NO messages and confirm it shows the welcome screen instead of the loading hang.
- [x] Task: Conductor - User Manual Verification 'Verification' (Protocol in workflow.md) baf46a9
