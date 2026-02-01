# Specification: Enhanced Interactive Questioning and Prompt Customization

## Overview
This track introduces two major enhancements to the Gemini Termux Agent:
1.  **Interactive Main Chat Questioning**: Enables the AI to ask structured, interactive questions (multiple-choice or open-ended) directly in the main chat, similar to the Prompt Helper.
2.  **Customizable Prompt Helper**: Adds a global Admin setting to customize the system prompt used by the Prompt Helper, allowing for tailored guidance.

## Functional Requirements

### 1. Interactive Questioning Protocol
*   **Trigger**: The AI can include a JSON block in its response to trigger an interactive question.
    *   Format: `{"type": "question", "question": "...", "options": [...], "allow_multiple": true/false}`.
*   **Detection**: The backend (`llm_service.py` or `chat.py`) will detect this JSON pattern.
*   **Rendering**: The frontend will render these as "Question Cards" inline with the chat messages.
    *   If `allow_multiple` is true, users can toggle multiple buttons and click a "Submit" button.
    *   If `allow_multiple` is false, clicking an option immediately submits the answer.
*   **Submission**: Submitting an answer sends the selection back to the AI as a user message, maintaining the conversation flow.

### 2. User Control
*   **Settings Toggle**: A new "Interactive Mode" toggle will be added to the User Settings (Security modal).
*   **System Prompt Injection**:
    *   If enabled, the global system prompt will include instructions on how to use the JSON questioning protocol.
    *   If disabled, the instructions will be omitted, and the AI will be told to use standard text only.

### 3. Admin Prompt Customization
*   **Admin UI**: A new text area in the Admin Dashboard to edit the "Prompt Helper System Instructions".
*   **Service Integration**: The `TreePromptService` will fetch this custom prompt from the configuration/database instead of using its hardcoded default.
*   **Global Scope**: This setting applies to all users.

## Technical Considerations
*   **Streaming Compatibility**: The frontend must handle JSON blocks appearing within the Server-Sent Events (SSE) stream.
*   **Fallback**: If JSON parsing fails, the raw text should be displayed as a fallback to ensure no content is lost.
*   **Config Storage**: The custom prompt should be stored in `config.py` or a dedicated settings file (e.g., `data/settings.json`).

## Acceptance Criteria
*   [ ] AI can successfully trigger a multiple-choice question in the main chat.
*   [ ] Users can toggle the interactive capability on/off in their settings.
*   [ ] Admin can update the Prompt Helper instructions and see the behavior change in the helper.
*   [ ] Interactive UI elements (buttons, multi-select) match the project's "Terminal-Inspired" aesthetic.
