# Implementation Plan - Stop Gemini Thinking

## User Review Required

> [!IMPORTANT]
> This plan assumes that the backend can interrupt the streaming response from the Gemini API. We will need to investigate if the current implementation of `llm_service.py` supports this natively or if we need to implement a manual interruption.

## Proposed Changes

### Frontend
- [x] Modify `app/templates/index.html` to include a "Stop" button.
- [x] Update `app/static/script.js` to handle the "Stop" button click.
- [x] Send a "cancel" signal to the backend (via WebSocket or a new POST endpoint).

### Backend
- [x] Create a new endpoint `/api/chat/stop` or handle a specific WebSocket message for cancellation.
- [x] Implement cancellation logic in `app/services/llm_service.py`.
- [x] Ensure that if a response is interrupted, the partial response is still saved if applicable, or the session remains consistent.

## Verification Plan

### Automated Tests
- [x] Create a test case in `tests/test_cancellation.py` that simulates a long-running request and then sends a cancel signal.
- [x] Verify that the stream is closed and the backend doesn't continue processing.

### Manual Verification
- [ ] Start a chat with a prompt that triggers a long response (e.g., "Write a 1000-word essay about AI").
- [ ] Click the "Stop" button.
- [ ] Verify that the response stops immediately.
- [ ] Verify that you can immediately send another message.
