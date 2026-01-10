# Specification: Streaming Responses (SSE)

## Overview
Implement real-time response streaming using Server-Sent Events (SSE) to prevent HTTP 504 timeouts on complex, long-running agent tasks. This will provide immediate feedback to the user and maintain a persistent connection during multi-step tool executions.

## Functional Requirements
- **SSE Implementation:** The `/chat` endpoint will be converted from a standard POST (JSON) to an SSE stream.
- **Backend Streaming:**
    - `GeminiAgent` will use `gemini --output-format stream-json` to capture real-time output from the CLI.
    - Chunks will be parsed and pushed to the SSE client immediately.
- **Tool Transparency (B):**
    - The stream will include "packets" for tool calls and tool outputs.
    - The UI will display these in collapsible code blocks or "log" areas within the current message bubble.
- **Buffered UI Rendering (C):**
    - `script.js` will use `EventSource` (or `fetch` with readable stream) to consume the SSE.
    - Incoming text will be buffered and the Markdown renderer (`marked`) will be triggered at a controlled frequency (e.g., every 100-200ms) to ensure a smooth "typing" effect without UI jitter.
- **Persistence:** Ensure the final complete message is still saved to the session history once the stream closes.

## Non-Functional Requirements
- **Reliability:** Handle network disconnects gracefully. If the stream breaks, the UI should show an error or try to resume.
- **Performance:** Ensure that frequent Markdown re-renders do not freeze the mobile browser.

## Acceptance Criteria
- [ ] The chat response begins appearing within seconds of clicking "Send", even for complex tasks.
- [ ] Users see tool execution details (calls and results) in real-time.
- [ ] Large responses no longer result in a "504 Gateway Timeout" error.
- [ ] The complete response is correctly saved in the chat history for future sessions.

## Out of Scope
- Implementing WebSockets (SSE is preferred).
- Ability to "Stop" a stream mid-way (this can be a future track).
