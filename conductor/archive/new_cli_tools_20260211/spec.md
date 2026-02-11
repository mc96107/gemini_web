# Specification: Gemini CLI Tool Integration Update

## Overview
This track involves updating the Gemini Web UI to support additional tools available in the current version of the Gemini CLI. Users will be able to enable/disable these tools via the "Tools Settings" modal on a per-session basis, maintaining the existing security-first approach where all tools are disabled by default.

## Functional Requirements
- **Tool Categorization:**
    - **Read-Only / Safe Tools:**
        - `cli_help`: Specialized in answering questions about Gemini CLI features and documentation.
        - `ask_user`: Allows the agent to ask the user one or more questions to gather preferences or clarify requirements.
        - `confirm_output`: Used to retrieve full output for previously previewed large results.
    - **Modification / High-Risk Tools:**
        - `activate_skill`: Enables specialized agent skills (e.g., `skill-creator`).
        - `codebase_investigator`: Specialized tool for deep codebase analysis and architectural mapping.
- **UI Updates:**
    - Add checkboxes/switches for the new tools in the `toolsModal` in `app/templates/index.html`.
    - Ensure new tools are properly styled within their respective categories (Safe vs. High-Risk).
- **Backend Integration:**
    - No changes required to `llm_service.py` as it dynamically passes enabled tools to the Gemini CLI.
- **Default State:**
    - All new tools must be disabled by default for new sessions.

## Non-Functional Requirements
- **Security:** Maintain strict per-session tool isolation.
- **Usability:** Ensure tool descriptions in the UI are clear and helpful.

## Acceptance Criteria
- [ ] The "Tools Settings" modal displays `cli_help`, `ask_user`, and `confirm_output` under "Read-Only / Safe Tools".
- [ ] The "Tools Settings" modal displays `activate_skill` and `codebase_investigator` under "Modification / High-Risk Tools".
- [ ] Selecting these tools and clicking "Apply Settings" correctly persists the choice for the active session.
- [ ] When enabled, the agent can successfully invoke these tools during a conversation.
- [ ] New sessions start with these tools disabled.

## Out of Scope
- Integration of Web Inspector tools (e.g., `navigate`, `click`, `inspect_dom`).
- Modification of actual Gemini CLI tool logic.