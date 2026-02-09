# Specification: Improve Auto Chat Naming

## Overview
Currently, the auto-generated chat names in the sidebar often include technical metadata such as system instructions (e.g., `[SYSTEM INSTRUCTION: ...]`) or file paths (e.g., `@tmp/user_attachments/...`). This makes the chat history cluttered and difficult to navigate. This track aims to filter out these elements from the initial user message before using it to generate the chat title.

## Functional Requirements
1.  **Metadata Filtering:**
    -   Exclude text wrapped in system instruction markers (e.g., `[SYSTEM INSTRUCTION: ... ]`).
    -   Exclude file path references, specifically those starting with `@` (e.g., `@tmp/user_attachments/file.txt`).
    -   Exclude strings matching standard file path regex patterns (e.g., `/absolute/path`, `C:\Windows\...`).
2.  **Name Generation Logic:**
    -   The chat name should be derived from the *remaining* text of the first user message after all filtering has been applied.
    -   The resulting string should be trimmed of leading/trailing whitespace.
    -   The name should be truncated to a reasonable length (e.g., 40-50 characters) to fit the sidebar.
3.  **Fallback Mechanism:**
    -   If the filtering process results in an empty or excessively short string (e.g., less than 3 characters), use a fallback name such as "New Conversation".

## Non-Functional Requirements
1.  **Efficiency:** The filtering logic should be lightweight and performed quickly during the chat initialization process.
2.  **Robustness:** The regex patterns should be broad enough to catch most common path formats without accidentally filtering out conversational text.

## Acceptance Criteria
- [ ] Chat sessions initialized with a system instruction in the first message do not include that instruction in their sidebar title.
- [ ] Chat sessions initialized with file attachments (using `@` paths) do not include the path strings in their sidebar title.
- [ ] If a first message contains *only* a system instruction and a file path, the chat title defaults to "New Conversation".
- [ ] Conversational text within the first message is correctly preserved and used for the title.

## Out of Scope
-   Dynamic AI-generated summaries for chat titles (this focuses on filtering the raw first message).
-   Retroactively renaming existing chat sessions.
