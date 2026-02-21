# Specification: User Default Model Selection

## Overview
Allow users to specify their preferred default AI model from a dropdown menu in the user settings. This setting will be persisted per-user and will determine which model is used for new chat sessions.

## Functional Requirements
- **Model Dropdown:** Add a dropdown menu to the "Preferences" section of the Security Settings modal.
- **Model Options:** The dropdown will include the following models:
  - Gemini 3 Pro (Stable)
  - Gemini 3 Flash (Stable)
  - Gemini 3 Pro Preview
  - Gemini 3 Flash Preview
  - Gemini 2.5 Pro
  - Gemini 2.5 Flash
- **Persistence:** The selected default model will be stored in the user's settings within `user_sessions.json`.
- **New Chat Behavior:** When a new chat session is initialized, it will automatically use the user's specified default model.
- **Immediate Effect:** If a user changes their default model while in an active chat, the current session's model will be updated to match the new selection immediately.

## Non-Functional Requirements
- **UI Consistency:** The dropdown should match the existing Bootstrap 5 dark theme aesthetic of the application.
- **Performance:** Setting retrieval and update should be fast and non-blocking.

## Acceptance Criteria
- [ ] Users can see a "Default Model" dropdown in the Security Settings -> Preferences section.
- [ ] Changing the selection in the dropdown persists the setting to the backend.
- [ ] Creating a "New Chat" uses the model selected in the user's default settings.
- [ ] Changing the default model while a chat is active updates the `model-input` value and the `model-label` text in the UI.

## Out of Scope
- Global (system-wide) default model changes (handled by admin via `.env` or global settings).
- Custom model names (only the standard set provided).
