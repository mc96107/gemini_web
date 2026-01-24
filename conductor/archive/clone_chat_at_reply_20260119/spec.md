# Specification: Clone Chat at Reply

## Overview
Allow users to fork a conversation at any specific Gemini reply. This creates a new session that contains the history up to that point, enabling the user to explore different conversational paths without losing the original one.

## Functional Requirements
- Add a "Clone" (fork) icon/button to every message in the chat (or at least Gemini replies).
- When pressed it will create an identical chat as the one up to that point of conversation.
- It will be done in the background, keeping the same tags and title of these chats.
- The user will be able to move between them with arrow buttons next to the fork chat icon.
- Add a button to show the chat as a tree which could also be used for navigation between chats.
- The tree button could be placed in the top bar (desktop) or in the right sidebar (mobile).
- When changing the chat title or tags, all forks will change also. This will happen in the background.

## Technical Requirements
- **Backend:**
    - New endpoint `POST /sessions/{uuid}/clone` taking `message_index`.
    - Logic to locate the session JSON file, clone it, and register it in `user_sessions.json`.
    - Logic to sync titles and tags across related sessions (forks).
- **Frontend:**
    - UI updates for the clone button on messages.
    - UI for "fork navigation" (arrows) next to messages that have branches.
    - A tree view modal to visualize branches.

## Data Model Changes
- `GeminiAgent` user data might need to track "related sessions" or "forks" explicitly.
- Add `parent_uuid` to session metadata to track the heritage.
- Add `fork_point` (message index) to session metadata.
