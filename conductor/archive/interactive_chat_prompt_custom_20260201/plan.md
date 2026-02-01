# Implementation Plan: Enhanced Interactive Questioning and Prompt Customization

This track implements structured interactive questioning in the main chat and allows global customization of the Prompt Helper's system instructions.

## Phase 1: Infrastructure & Admin Settings [checkpoint: 37b49c7]
Implement the foundational storage and Admin UI for the new settings.

- [x] Task: Create `data/settings.json` to store global configuration. 39d6d75
- [x] Task: Update `app/core/config.py` to load and provide access to global settings. 39d6d75
- [x] Task: Add "Prompt Helper Instructions" text area to the Admin Dashboard (`app/templates/admin.html`). 8ee5f11
- [x] Task: Implement backend routes in `app/routers/admin.py` to get and save these global settings. 8ee5f11
- [x] Task: Conductor - User Manual Verification 'Phase 1: Infrastructure & Admin Settings' (Protocol in workflow.md) f66db62

## Phase 2: Backend Protocol Implementation [checkpoint: 84e94a5]
Enhance the backend to support the JSON questioning protocol and per-user toggles.

- [x] Task: Add `interactive_mode` boolean to user settings in `AgentModel` and `user_sessions.json`. 7cb342d
- [x] Task: Implement a system prompt injector that adds the "Interactive Questioning" instructions to the session if the user has it enabled. 08b0256
- [x] Task: Update `app/services/llm_service.py` to detect and parse the `{"type": "question", ...}` JSON block in the stream. 22d0504
- [x] Task: Ensure the parsed question data is correctly wrapped in the SSE stream sent to the frontend. 8442eba
- [x] Task: Conductor - User Manual Verification 'Phase 2: Backend Protocol Implementation' (Protocol in workflow.md) b2b2196

## Phase 3: Frontend Interactive Components [checkpoint: d7596df]
Create the UI components to render and interact with the questions.

- [x] Task: Implement the "Question Card" UI component in `app/static/script.js` and `app/static/style.css`. 398137d
- [x] Task: Handle multiple-choice (single and multi-select) interactions in the chat interface. 398137d
- [x] Task: Implement the submission logic that sends the user's choice back as a standard message. 398137d
- [x] Task: Add the "Interactive Mode" toggle to the User Security/Settings modal. 685825a
- [x] Task: Conductor - User Manual Verification 'Phase 3: Frontend Interactive Components' (Protocol in workflow.md) 841b483

## Phase 4: Prompt Helper Customization [checkpoint: 76e1f14]
Connect the Prompt Helper to the new customizable instructions.

- [x] Task: Modify `app/services/tree_prompt_service.py` to use the global "Prompt Helper Instructions" from settings. a14937a
- [x] Task: Add a "Reset to Default" button for the helper instructions in the Admin UI. a14937a
- [x] Task: Verify that the Prompt Helper respects the new instructions during a guided session. a14937a
- [x] Task: Conductor - User Manual Verification 'Phase 4: Prompt Helper Customization' (Protocol in workflow.md) a129990

## Phase 5: Verification & Polishing [checkpoint: f6597e3]
Final testing and UI/UX refinements.

- [x] Task: Write integration tests for the interactive questioning flow. ca5cc1e
- [x] Task: Perform end-to-end testing of the Admin customization. 94ebe56
- [x] Task: Refine the "Question Card" aesthetic to ensure it feels native to the terminal-inspired theme. 422e8bd
- [x] Task: Conductor - User Manual Verification 'Phase 5: Verification & Polishing' (Protocol in workflow.md) 841b483

## Phase 6: Customizable Interactive Mode Instructions
Allow administrators to customize the system instructions used for interactive questioning in the main chat.

- [x] Task: Add `interactive_mode_instructions` to `data/settings.json` and update Admin UI. e700960
- [x] Task: Update `app/services/llm_service.py` to use the global "Interactive Mode Instructions" from settings. 42039f6
- [x] Task: Update `tests/test_user_settings.py` to verify customization of main chat interactive behavior. 42039f6


