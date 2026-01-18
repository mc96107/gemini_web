# Implementation Plan - Tagging System

## User Review Required

> [!IMPORTANT]
> Should tags be global per user or specific to some context? We'll assume global per user for now.
> How should auto-tagging behave? Should it happen on every message or just at the start?

## Proposed Changes

### Data Model & Backend
- [ ] Update chat storage schema to support `tags` (list of strings).
- [ ] Implement tag management in backend services.
- [ ] Add API endpoints for updating tags and fetching unique tags.

### Frontend
- [ ] Add tag display and editing UI to the chat interface.
- [ ] Implement tag filtering in the sidebar.
- [ ] Update sidebar to support multi-tag selection.

### Auto-tagging
- [ ] Implement a basic auto-tagging service that suggests tags based on conversation content.

## Verification Plan

### Automated Tests
- [ ] Test adding/removing tags via API.
- [ ] Test filtering chats by tags in the backend logic.
- [ ] Test fetching unique tags.

### Manual Verification
- [ ] Create a chat and add tags "work" and "urgent".
- [ ] Filter by "work" and verify the chat appears.
- [ ] Add another chat with "personal" tag.
- [ ] Filter by "work" and verify "personal" chat is hidden.
- [ ] Filter by both "work" and "personal".
