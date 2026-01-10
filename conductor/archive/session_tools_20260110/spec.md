# Specification: Per-Session Tool Configuration

## Overview
Implement a security-first tool configuration system that allows users to selectively enable Gemini CLI tools on a per-session basis. By default, all tools are disabled to prevent unauthorized or harmful operations. Settings are persisted within the chat session to ensure preferences remain active across browser reloads or return visits.

## Functional Requirements
- **Per-Session Isolation:** Tool permissions must be unique to each chat session. Enabling a tool in "Session A" does not enable it in "Session B".
- **Default State:** All tools (e.g., `run_shell_command`, `write_file`) must be disabled by default for new sessions.
- **Tools Settings UI:**
    - A tools icon (e.g., a gear or wrench) will be added **near the message input field** in the chat interface.
    - Clicking the icon opens a **Configuration Modal** for the current session.
- **Configuration Modal Features:**
    - **Risk-Based Grouping:**
        - **Read-Only/Safe Tools:** `list_directory`, `read_file`, `glob`, `search_file_content`, `google_web_search`, `web_fetch`.
        - **Modification/High-Risk Tools:** `replace`, `write_file`, `run_shell_command`, `save_memory`, `delegate_to_agent`.
    - **Selection:** Individual toggles for each tool.
    - **Mass Action:** A "Deselect All" button for quick resets.
- **Persistence:** Tool settings must be saved in the session state (backend storage) so they persist when the user returns to the chat.
- **Enforcement:** The `llm_service` or equivalent must check the session-specific tool configuration before allowing any tool execution.

## Non-Functional Requirements
- **Security:** Ensure that tool execution is blocked if the corresponding tool is not explicitly enabled in the current session context.
- **UI Consistency:** Use Bootstrap 5 components (modals, switches/toggles) to match the existing tech stack.

## Acceptance Criteria
- [ ] Users see a tool icon near the message input field.
- [ ] Clicking the icon opens a modal showing tools grouped by risk level for the active session.
- [ ] Settings changed in the modal are saved and persist after refreshing the page or switching sessions.
- [ ] If a tool is disabled in the UI, the backend refuses to execute it even if requested by the LLM.
- [ ] "Deselect All" successfully disables all tool toggles in the modal.

## Out of Scope
- Global tool configuration (all settings are per-session).
- Fine-grained permission parameters (e.g., restricting `run_shell_command` to specific directories).
