# Specification: Copy Formatted Text to Clipboard

This track adds a user-configurable option to copy message content either as raw Markdown or as formatted Rich Text (HTML). A new toggle will be added to the User Settings to control this behavior.

## Functional Requirements

### 1. User Settings Update
- Add a new toggle labeled **"Copy Formatted Text"** in the "Security Settings" (User Settings) modal.
- The toggle state must be persisted per user in `user_sessions.json`.
- **Default behavior:** The toggle is **OFF**, meaning the copy button will continue to copy raw Markdown text by default.

### 2. Message Copy Button Enhancement
- The existing copy button on AI and User messages will remain in its current position.
- When the "Copy Formatted Text" toggle is **OFF**:
    - Clicking the copy button copies the raw Markdown string to the clipboard (current behavior).
- When the "Copy Formatted Text" toggle is **ON**:
    - Clicking the copy button copies the message content as both **Rich Text (HTML)** and **Plain Text**.
    - This allows users to paste the content into applications like Microsoft Word, Google Docs, or email clients while preserving bold, italics, links, and code formatting.

## Technical Details

### Backend
- Update `GeminiAgent.get_user_settings` and `update_user_settings` in `app/services/llm_service.py` to include `copy_formatted` (boolean).
- Update the default settings object to `{"show_mic": True, "interactive_mode": True, "copy_formatted": False}`.

### Frontend
- **HTML:** Update `app/templates/index.html` to include the checkbox in the `#securityModal`.
- **JavaScript:** 
    - Update `app/static/script.js` to sync the toggle state with the backend.
    - Modify the `copyBtn.onclick` handler to check `window.USER_SETTINGS.copy_formatted`.
    - Use the `ClipboardItem` API for rich text copying:
      ```javascript
      const blob = new Blob([htmlContent], { type: 'text/html' });
      const plainBlob = new Blob([textContent], { type: 'text/plain' });
      const item = new ClipboardItem({
          'text/html': blob,
          'text/plain': plainBlob
      });
      navigator.clipboard.write([item]);
      ```

## Acceptance Criteria
- [ ] Users can toggle "Copy Formatted Text" in the settings modal.
- [ ] The setting persists after page reloads.
- [ ] With the setting ON, pasting into a rich text editor preserves formatting.
- [ ] With the setting OFF, pasting results in raw Markdown text.
