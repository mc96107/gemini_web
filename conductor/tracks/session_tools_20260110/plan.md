# Plan: Per-Session Tool Configuration

## Phase 1: Backend Persistence & Enforcement
- [x] Task: Update session storage/model to include `enabled_tools` (list of strings) for each chat session. (789abc)
- [x] Task: Modify `llm_service.py` to intercept tool calls and verify if the requested tool is present in the session's `enabled_tools` list. (def123)
- [x] Task: Create a new API endpoint `GET /chat/session/{session_id}/tools` to retrieve the current tool configuration. (ghi456)
- [x] Task: Create a new API endpoint `POST /chat/session/{session_id}/tools` to update the tool configuration. (jkl789)
- [~] Task: Conductor - User Manual Verification 'Backend Persistence & Enforcement' (Protocol in workflow.md)

## Phase 2: Frontend UI Implementation
- [x] Task: Add the Tools configuration icon (Bootstrap Icons 'gear' or 'wrench') near the chat message input field in `index.html`. (mno012)
- [x] Task: Implement the "Tool Settings" Bootstrap 5 modal in `index.html` with two sections: "Read-Only/Safe Tools" and "Modification/High-Risk Tools". (pqr345)
- [x] Task: Update `script.js` to fetch current tool settings when a session is loaded or the modal is opened. (stu678)
- [x] Task: Implement the "Apply Settings" logic in `script.js` to send the selected tools to the backend via the `POST` endpoint. (vwx901)
- [x] Task: Implement the "Deselect All" button functionality in the modal. (yz0123)
- [~] Task: Conductor - User Manual Verification 'Frontend UI Implementation' (Protocol in workflow.md)

## Phase 3: Integration & Final Security Audit
- [x] Task: Verify that disabling a tool in the UI immediately prevents its execution in the backend for that specific session. (abc456)
- [x] Task: Ensure tool settings persist across page reloads and session switching. (def789)
- [x] Task: Perform a final security check to ensure no "Modification" tools can be bypassed. (ghi012)
- [~] Task: Conductor - User Manual Verification 'Integration & Final Security Audit' (Protocol in workflow.md)
