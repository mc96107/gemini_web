# Implementation Plan: User Default Model Selection

## Phase 1: Backend Infrastructure & Persistence [checkpoint: 975f25c]
- [x] Task: Update `GeminiAgent` to support `default_model` setting [bf7237b]
    - [x] Modify `GeminiAgent._load_user_data` to ensure `default_model` has a default value (e.g., `gemini-3-pro-preview`).
    - [x] Verify `get_user_settings` and `update_user_settings` correctly handle the new field.
- [x] Task: Red Phase - Write unit tests for user settings persistence [bf7237b]
    - [x] Create `tests/test_user_model_settings.py`.
    - [x] Write tests to verify saving and retrieving `default_model` per user.
- [x] Task: Green Phase - Implement backend changes [bf7237b]
    - [x] Run tests and ensure they pass.
- [x] Task: Conductor - User Manual Verification 'Phase 1: Backend Infrastructure & Persistence' (Protocol in workflow.md) [975f25c]

## Phase 2: Frontend UI - Settings & Interaction [checkpoint: 53970e0]
- [x] Task: Update `index.html` with Model Dropdown [f517d01]
    - [x] Add a `<select>` or dropdown menu for "Default Model" in the Security Modal -> Preferences section.
    - [x] Populate with the specified models: Gemini 3 Pro, Gemini 3 Flash (Stable/Preview) and Gemini 2.5 Pro/Flash.
- [x] Task: Update `script.js` for settings sync [f517d01]
    - [x] Add event listener for the new dropdown to call `/settings` endpoint on change.
    - [x] Update `loadUserSettings` (if it exists) or initialization logic to set the dropdown value.
- [x] Task: Implement immediate UI update logic [f517d01]
    - [x] Ensure that changing the default model dropdown also updates the current active session's `model-input` and `model-label`.
- [x] Task: Red Phase - Write integration tests for settings UI [f517d01]
    - [x] Create/Update tests to verify that changing the dropdown sends the correct request and updates the local state.
- [x] Task: Green Phase - Implement frontend changes [f517d01]
    - [x] Run tests and ensure they pass.
- [x] Task: Conductor - User Manual Verification 'Phase 2: Frontend UI - Settings & Interaction' (Protocol in workflow.md) [53970e0]

## Phase 3: Integration & New Chat Logic [checkpoint: cf98fcd]
- [x] Task: Connect New Chat button to Default Model [f517d01]
    - [x] Modify the "New Chat" click handler in `script.js` to ensure the `model-input` is set to the user's `default_model` before starting the session.
- [x] Task: Final Verification & Polish [ee62ad3]
    - [x] Verify the end-to-end flow: Login -> Set Default Model -> New Chat -> Confirm Model Used.
    - [x] Ensure mobile responsiveness of the new dropdown.
- [x] Task: Conductor - User Manual Verification 'Phase 3: Integration & New Chat Logic' (Protocol in workflow.md) [cf98fcd]
