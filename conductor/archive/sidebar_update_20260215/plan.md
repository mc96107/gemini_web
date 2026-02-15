# Implementation Plan - Fix: New Chat Sidebar Update

## Phase 1: Diagnostics and Baseline
- [ ] Task: Research current message sending flow in `app/static/script.js` to identify where the sidebar update is missing.
- [ ] Task: Verify how session IDs are handled in the frontend state versus the URL.
- [ ] Task: Conductor - User Manual Verification 'Phase 1: Diagnostics and Baseline' (Protocol in workflow.md)

## Phase 2: Frontend Implementation
- [ ] Task: Write Tests: Create a Vitest or similar test case (if applicable) or a manual reproduction script to verify sidebar stale state.
- [ ] Task: Implement: Modify the message sending logic in `app/static/script.js` to trigger a sidebar refresh after the first message is sent.
- [ ] Task: Implement: Ensure the sidebar refresh logic uses existing `loadHistory` or similar functions without altering the URL.
- [ ] Task: Conductor - User Manual Verification 'Phase 2: Frontend Implementation' (Protocol in workflow.md)

## Phase 3: Verification
- [ ] Task: Write Tests: Verify that starting a new chat correctly updates the sidebar.
- [ ] Task: Write Tests: Verify that the URL remains unchanged after the sidebar update.
- [ ] Task: Conductor - User Manual Verification 'Phase 3: Verification' (Protocol in workflow.md)

## Phase: Review Fixes
- [x] Task: Apply review suggestions c9f5864
