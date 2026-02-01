# Implementation Plan: Enhanced Interactive Questioning and Prompt Customization

This track implements structured interactive questioning in the main chat and allows global customization of the Prompt Helper's system instructions.

## Phase 1: Infrastructure & Admin Settings [checkpoint: 37b49c7]
Implement the foundational storage and Admin UI for the new settings.

- [x] Task: Create `data/settings.json` to store global configuration. 39d6d75
- [x] Task: Update `app/core/config.py` to load and provide access to global settings. 39d6d75
- [x] Task: Add "Prompt Helper Instructions" text area to the Admin Dashboard (`app/templates/admin.html`). 8ee5f11
- [x] Task: Implement backend routes in `app/routers/admin.py` to get and save these global settings. 8ee5f11
- [x] Task: Conductor - User Manual Verification 'Phase 1: Infrastructure & Admin Settings' (Protocol in workflow.md) f66db62
- [ ] Task: Conductor - User Manual Verification 'Phase 1: Infrastructure & Admin Settings' (Protocol in workflow.md)

## Phase 2: Backend Protocol Implementation
Enhance the backend to support the JSON questioning protocol and per-user toggles.

- [x] Task: Add `interactive_mode` boolean to user settings in `AgentModel` and `user_sessions.json`. 7cb342d
- [~] Task: Implement a system prompt injector that adds the "Interactive Questioning" instructions to the session if the user has it enabled.
- [ ] Task: Update `app/services/llm_service.py` to detect and parse the `{"type": "question", ...}` JSON block in the stream.
- [ ] Task: Ensure the parsed question data is correctly wrapped in the SSE stream sent to the frontend.
- [ ] Task: Conductor - User Manual Verification 'Phase 2: Backend Protocol Implementation' (Protocol in workflow.md)

## Phase 3: Frontend Interactive Components
Create the UI components to render and interact with the questions.

- [ ] Task: Implement the "Question Card" UI component in `app/static/script.js` and `app/static/style.css`.
- [ ] Task: Handle multiple-choice (single and multi-select) interactions in the chat interface.
- [ ] Task: Implement the submission logic that sends the user's choice back as a standard message.
- [ ] Task: Add the "Interactive Mode" toggle to the User Security/Settings modal.
- [ ] Task: Conductor - User Manual Verification 'Phase 3: Frontend Interactive Components' (Protocol in workflow.md)

## Phase 4: Prompt Helper Customization
Connect the Prompt Helper to the new customizable instructions.

- [ ] Task: Modify `app/services/tree_prompt_service.py` to use the global "Prompt Helper Instructions" from settings.
- [ ] Task: Add a "Reset to Default" button for the helper instructions in the Admin UI.
- [ ] Task: Verify that the Prompt Helper respects the new instructions during a guided session.
- [ ] Task: Conductor - User Manual Verification 'Phase 4: Prompt Helper Customization' (Protocol in workflow.md)

## Phase 5: Verification & Polishing
Final testing and UI/UX refinements.

- [ ] Task: Write integration tests for the interactive questioning flow.
- [ ] Task: Perform end-to-end testing of the Admin customization.
- [ ] Task: Refine the "Question Card" aesthetic to ensure it feels native to the terminal-inspired theme.
- [ ] Task: Conductor - User Manual Verification 'Phase 5: Verification & Polishing' (Protocol in workflow.md)
