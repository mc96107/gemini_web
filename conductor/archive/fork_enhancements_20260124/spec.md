# Specification - Fork Enhancements (Permissions & Branding)

## Overview
This track focuses on refining the "Clone/Fork Chat" functionality. Currently, when a chat is forked, tool permissions and tags are not preserved, requiring users to manually re-enable tools and re-add tags. Additionally, the visual representation of a "branch" or "fork" uses a generic tree icon that will be updated to a more standard git-style fork icon.

## Functional Requirements
*   **Tool Permission Inheritance:** When a user forks a chat from a Gemini reply, the new chat session must automatically inherit the exact same enabled/disabled state of all tools from the original session.
*   **Tag Inheritance:** The new forked chat session must inherit all manual and auto-generated tags from the original session.
*   **Icon Refresh:** Replace all instances of the current "tree" icon used for forks (specifically in the sidebar/chat history) with the provided SVG fork icon.

## Non-Functional Requirements
*   **Performance:** Inheritance of permissions and tags should be instantaneous and not add perceptible delay to the forking process.
*   **Security:** Ensure that only the tool *state* (enabled/disabled) is copied, maintaining the existing per-session security boundaries.

## Acceptance Criteria
*   [ ] Forking a chat with `bash` and `filesystem` tools enabled results in a new chat where `bash` and `filesystem` are also enabled.
*   [ ] Forking a chat with tags "Project A" and "Bug" results in a new chat also tagged with "Project A" and "Bug".
*   [ ] The sidebar displays the new fork SVG icon instead of the old tree icon for all forked chats.
*   [ ] The "Fork" button next to Gemini messages uses the new fork icon.

## Out of Scope
*   Preserving transient tool state (e.g., current working directory if changed mid-session, unless part of the base tool config).
*   Syncing future tag/tool changes between the original and the fork after the initial creation.