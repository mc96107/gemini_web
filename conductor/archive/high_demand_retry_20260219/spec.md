# Specification - Track: High Demand Retry/Stop UI

## Overview
Implement a structured user intervention (Retry/Stop) in the web interface when the backend Gemini CLI encounters a "High Demand" (429/503) error and requires user guidance on whether to continue. This matches the native Gemini CLI behavior but provides a web-optimized interactive experience using Question Cards.

## Functional Requirements
*   **Trigger Mechanism:** The backend (`llm_service` or `agent_manager`) must detect the "High Demand" signal from the Gemini CLI.
*   **Interactive Questioning:** When triggered, the UI must display a "Question Card" in the chat history with the message: "We are currently experiencing high demand. Should I keep trying?"
*   **"Retry" Action:**
    *   Clicking "Retry" sends a signal back to the Gemini CLI (simulating the 'r' or 'retry' input) to attempt the request again.
    *   The Question Card should be marked as answered.
*   **"Stop" Action:**
    *   Clicking "Stop" triggers the existing interrupt mechanism (sending a SIGINT to the CLI process).
    *   The chat session should reflect that the request was cancelled.
    *   The Question Card should be marked as answered.

## Non-Functional Requirements
*   **Responsiveness:** The "Retry/Stop" card must appear instantly in the SSE stream.
*   **State Persistence:** If the user refreshes the page while the card is active, it should re-render correctly from the session state.

## Acceptance Criteria
- [ ] Backend correctly identifies the "High Demand" state from CLI output/errors.
- [ ] A Question Card with "Retry" and "Stop" buttons appears in the web chat when high demand occurs.
- [ ] Clicking "Retry" resumes the CLI operation.
- [ ] Clicking "Stop" immediately interrupts the CLI process and stops the generation.
- [ ] The interaction is recorded in the chat history.

## Out of Scope
*   Modifying the backend's automatic model fallback logic (assumed already implemented).
*   Automatic background retries without user intervention (unless specifically requested later).
