# Specification: Fix Session Loading UI Hang & CSP Issues

## Overview
Users report that the chat interface hangs on "Loading conversation..." when switching sessions. Console logs indicate Content Security Policy (CSP) violations blocking connections to external source maps (CDN). While source map blocks shouldn't break functionality, they indicate an overly restrictive CSP. The primary issue is likely a UI state management bug where the loading placeholder isn't cleared when a session is empty or fails silently.

## Functional Requirements
- **Proper State Clearing:** Ensure that the "Loading conversation..." placeholder is reliably removed from the `chat-container` regardless of whether the session has messages or is empty.
- **Empty Session Handling:** If a session is loaded but contains no messages, explicitly clear the loading placeholder and show the "Chat Welcome" screen.
- **CSP Update:** Update the Content Security Policy in `app/main.py` to allow connections to CDN providers for source maps (or simply allow `https:` in `connect-src` if appropriate for this dev tool), eliminating the console errors.
- **Error Handling:** Ensure that if `fetch` fails or returns empty, the UI recovers gracefully.

## Acceptance Criteria
- [ ] Switching to an empty session clears "Loading conversation..." and shows the welcome screen.
- [ ] Console errors regarding `connect-src` violations for Bootstrap/CDN source maps are resolved.
- [ ] Switching between sessions is smooth and never leaves the UI in a "Loading..." state indefinitely.

## Out of Scope
- Backend performance optimization.
