# Specification: Streaming Robustness

## Overview
Users occasionally encounter "Connection lost" errors during long-running AI responses. This is often due to network timeouts or proxy interruptions when no data is sent for several seconds. We will implement heartbeats and improved error handling to make the connection more resilient.

## Functional Requirements
- **SSE Keep-Alives:** The server should send periodic heartbeat signals (e.g., `: keep-alive` comments) during long-running generations to prevent connection idle timeouts.
- **Improved Error Catching:** Ensure that backend exceptions during subprocess execution are caught and streamed as structured error messages instead of terminating the connection abruptly.
- **Frontend Resilience:** Update the frontend stream reader to handle unexpected closures more gracefully and provide more descriptive feedback.

## Acceptance Criteria
- [ ] Connections remain active during long (60s+) AI generations.
- [ ] Server-side errors are displayed in the chat UI as red error blocks instead of generic connection lost messages.
- [ ] No regressions in streaming performance or message rendering.
