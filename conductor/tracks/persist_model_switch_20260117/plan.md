# Implementation Plan - Persist Model Switch on Quota Exhaustion

## Proposed Changes

### Frontend
- [x] Update `model_switch` handler in `app/static/script.js` to update `modelInput.value`.
- [x] Update `model_switch` handler in `app/static/script.js` to update active state in model menu.

## Verification Plan

### Manual Verification
- [ ] Simulate a 429 error from the backend (or trigger it naturally).
- [ ] Observe the `model_switch` event in the chat.
- [ ] Verify that the model label in the footer updates to "Gemini 3 Flash (Auto-switched)".
- [ ] Verify that clicking the model menu shows "Flash" as the active selection.
- [ ] Send another message and verify (via network logs or `agent_debug.log`) that it uses the Flash model without needing another fallback.
