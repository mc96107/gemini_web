# Implementation Plan - Chat Export

## Phase 1: Implementation
- [x] Task: Add Export Button
    - [x] Add an "Export" button to the header in `app/templates/index.html`.
- [x] Task: Implement Export Logic
    - [x] In `app/static/script.js`, add an event listener for the Export button.
    - [x] Fetch all messages for the current session (handle pagination if necessary, or use a separate API call if needed, but client-side collection of loaded messages + fetch rest might be complex. Better: Fetch *all* messages for export via a specific call or iterate).
    - *Refinement:* Since `get_session_messages` supports `limit` and `offset`, we can fetch all by setting a large limit or looping.
    - [x] Format as Markdown string.
    - [x] Trigger download using a `Blob` and `<a>` tag.
- [x] Task: Conductor - User Manual Verification 'Chat Export' (Protocol in workflow.md) ba03c41
