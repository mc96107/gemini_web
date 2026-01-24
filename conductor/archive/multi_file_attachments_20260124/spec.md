# Specification: Ability to Attach Multiple Files

## Overview
This feature allows users to attach multiple files (images, documents, etc.) to a single chat message. It enhances the current single-file upload capability by providing a more flexible and efficient way to share context with the AI agent.

## Functional Requirements
- **Multi-File Selection:** Users can select multiple files simultaneously using the standard system file picker (via `multiple` attribute on the file input).
- **Drag-and-Drop Upload:** A dedicated zone in the chat interface allows users to drag and drop multiple files to initiate the upload process.
- **Attachment Queue:** An interactive list/queue of pending attachments is displayed before the message is sent. 
    - Users can remove individual files from the queue.
    - Thumbnails are shown for images; generic file icons with names are shown for other types.
- **Client-Side Compression:** Images are automatically compressed as they are added to the queue. The compressed versions are used for both the preview and the final upload.
- **Cumulative Size Validation:**
    - The system enforces a total cumulative size limit for all files in the queue.
    - Total size is calculated based on the *compressed* size of images and the original size of other files.
    - If a new file addition causes the total size to exceed the limit, an immediate alert is shown to the user, and the file is not added.

## Non-Functional Requirements
- **Performance:** Adding and compressing files should be handled asynchronously to avoid blocking the main UI thread.
- **Security:** Maintain existing per-session tool security and data privacy standards.

## Acceptance Criteria
- [ ] Users can select more than one file in the file picker.
- [ ] Dragging and dropping files into the UI adds them to the attachment queue.
- [ ] The attachment queue correctly displays all pending files with appropriate previews/icons.
- [ ] Removing a file from the queue works correctly and updates the total size calculation.
- [ ] Images are compressed upon being added to the queue.
- [ ] Adding files that exceed the cumulative size limit triggers an immediate warning and prevents the addition.
- [ ] Messages are sent with all queued attachments successfully.

## Out of Scope
- Server-side file processing beyond current capabilities.
- Advanced file editing or annotation features.
