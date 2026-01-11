# Implementation Plan - Fix Session Loading & CSP

## Phase 1: CSP and UI Fixes
- [x] Task: Update CSP in `app/main.py` 8a05af8
    - [x] Update `SecurityHeadersMiddleware` to allow `connect-src` to `cdn.jsdelivr.net`.
- [ ] Task: Fix UI Loading Hang in `app/static/script.js`
    - [ ] Locate the session switching logic (where "Loading conversation..." is injected).
    - [ ] Ensure `loadMessages` properly handles the `chatContainer` content clearing.
    - [ ] Add a safety check in `loadMessages` to remove any existing "Loading conversation..." message if it's the first page (`offset === 0`).
- [ ] Task: Conductor - User Manual Verification 'CSP and UI Fixes' (Protocol in workflow.md)

## Phase 2: Verification
- [ ] Task: Verify CSP Fix
    - [ ] Refresh the page and confirm the console no longer shows `connect-src` violations for CDN resources.
- [ ] Task: Verify Session Switching
    - [ ] Switch to a session with messages and confirm it loads correctly.
    - [ ] Switch to a session with NO messages and confirm it shows the welcome screen instead of the loading hang.
- [ ] Task: Conductor - User Manual Verification 'Verification' (Protocol in workflow.md)
