# Specification - Add a Way to Rename Chat

## Problem
Currently, chat titles are either automatically generated or fixed. Users have no way to manually rename a chat session to make it easier to find later.

## Proposed Solution
- Add a rename icon/button next to the chat title in the sidebar or the main chat header.
- When clicked, allow the user to edit the title.
- Update the backend to persist the new title.

## Requirements
- UI: Edit button (pencil icon) in the sidebar chat list.
- UI: Inline editing or a modal to enter the new name.
- Backend: Endpoint to update the chat title in the database/storage.
- Persistence: Ensure the name change is reflected across sessions and in the chat history.
