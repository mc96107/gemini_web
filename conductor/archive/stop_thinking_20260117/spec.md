# Specification - Stop Gemini Thinking

## Problem
Users currently have no way to interrupt Gemini once it starts generating a response or thinking about a tool call. This can be problematic if the user realizes they made a mistake in the prompt or if the response is taking too long.

## Proposed Solution
- Add a "Stop" button to the UI that is only visible when Gemini is in the "thinking" or "responding" state.
- Implement a mechanism in the backend to cancel the current stream or tool execution.
- Update the frontend to handle the cancellation gracefully and allow the user to send a new message.

## Requirements
- UI: A visible "Stop" button (square icon) near the input area or as an overlay on the responding message.
- Backend: Endpoint or WebSocket message to signal cancellation.
- Service: `llm_service.py` should support interrupting the request to Google's API.
- State Management: Ensure the UI state is reset correctly after stopping.
