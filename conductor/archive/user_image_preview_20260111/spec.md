# Specification: User Message Image Preview

## Overview
Enhance the chat interface by displaying a thumbnail preview of uploaded images directly within the user's message bubble. This provides immediate visual confirmation of the attachment and improves the overall user experience.

## Functional Requirements
- **Thumbnail Generation:** When an image is uploaded with a message, generate a thumbnail preview.
- **UI Placement:** The thumbnail should be displayed at the top of the user's message bubble, above any accompanying text.
- **Fixed Sizing:** Thumbnails should have a fixed maximum dimension (e.g., 150px) to maintain a consistent bubble size.
- **Interactive Preview:** Clicking the thumbnail should open the full-sized image in a new browser tab or a simple lightbox modal.
- **Persistence:** Ensure previews are also displayed when loading historical messages from a session.

## Non-Functional Requirements
- **Efficiency:** Use CSS `object-fit: cover` to ensure thumbnails look good regardless of original aspect ratio.
- **Security:** Ensure image URLs are correctly handled via the existing `tmp/user_attachments` routing.

## Acceptance Criteria
- [ ] User message bubbles containing images now show a small (150px) preview.
- [ ] The preview appears above the text.
- [ ] Clicking the preview opens the full image.
- [ ] Refreshing the page or switching sessions correctly restores the image previews in the history.

## Out of Scope
- Server-side thumbnail generation (previews will be handled by the browser using the uploaded file's URL).
- Advanced image editing or manipulation within the UI.
