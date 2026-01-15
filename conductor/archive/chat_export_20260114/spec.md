# Specification: Chat Export

## Overview
Allow users to export the current chat session's history as a Markdown file. This provides a way to save and share conversations offline.

## Functional Requirements
- **UI:** Add an "Export Chat" button, likely in the header or sidebar (e.g., near the Reset button).
- **Format:** Export format should be Markdown (`.md`).
- **Content:** Include both User and Bot messages, clearly formatted.
- **Filename:** Default filename should include the session title or timestamp.

## Acceptance Criteria
- [ ] Clicking "Export" triggers a download of a `.md` file.
- [ ] The downloaded file contains the full conversation history.
