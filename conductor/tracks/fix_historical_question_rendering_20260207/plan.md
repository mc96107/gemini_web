# Plan: Fix Historical Interactive Question Rendering

## Phase 1: Research & Setup
- [x] Task: Identify the exact structure of "Structured Interactive Questioning" JSON data by examining `app/services/llm_service.py` or `app/services/agent_manager.py`.
- [x] Task: Create a reproduction test case (HTML/JS) that loads a mock chat history containing Question Card JSON to verify the bug.

## Phase 2: Refactor Frontend Rendering
- [x] Task: Refactor `renderQuestionCard` in `app/static/script.js` to return a DOM element instead of appending directly to `chatContainer`.
- [x] Task: Update `createMessageDiv` in `app/static/script.js` to detect if a message's content is a valid Question Card JSON.
- [x] Task: Integrate the refactored question card creation into `createMessageDiv` so historical questions render as UI cards.
- [x] Task: Ensure that reloaded question cards are correctly sized and styled within the chat history flow.

## Phase 3: Verification
- [x] Task: Run the reproduction test case to confirm the fix.
- [x] Task: Manually verify by creating a chat with interactive questions, refreshing the page, and confirming they render as cards.
- [x] Task: Verify that answered questions maintain a consistent state (e.g., still show the answer or remain functional) when reloaded.
- [x] Task: Conductor - User Manual Verification 'Phase 3: Verification' (Protocol in workflow.md)
