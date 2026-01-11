# Implementation Plan - User Message Image Preview

## Phase 1: Infrastructure and UI Logic
- [x] Task: Serve Uploaded Attachments 465c7dd
    - [x] Add a route or mount `UPLOAD_DIR` in `app/main.py` to serve files to the browser.
    - [x] Route should be something like `/uploads/{filename}`.
- [x] Task: Implement Image Preview Logic in `app/static/script.js` 5e1d115
    - [x] Update `createMessageDiv` to detect image attachments.
    - [x] For new uploads: Use `URL.createObjectURL(file)` to show an immediate thumbnail.
    - [x] For history: Parse strings like `@tmp/user_attachments/filename` and convert them to the new serving URL.
    - [x] Insert an `<img>` tag with a class like `message-thumbnail`.
    - [x] Fix: Explicitly serve WebP files with `image/webp` MIME type in `app/main.py`.
- [x] Task: Add Styling and Interaction 5e1d115
    - [x] Add CSS to `app/static/style.css` for `.message-thumbnail` (max-width: 150px, border-radius, cursor: pointer).
    - [x] Add a click listener to thumbnails to open the full image in a new tab.
- [x] Task: Conductor - User Manual Verification 'Infrastructure and UI Logic' (Protocol in workflow.md) 5e1d115

## Phase 2: Verification
- [x] Task: Verify Immediate Preview 5e1d115
    - [x] Upload an image and confirm the thumbnail appears correctly in the user bubble.
- [x] Task: Verify History Preview 5e1d115
    - [x] Refresh the page/switch sessions and confirm that historical images also display thumbnails.
- [x] Task: Verify Full Image View 5e1d115
    - [x] Click a thumbnail and confirm the full-sized image opens as expected.
- [x] Task: Conductor - User Manual Verification 'Verification' (Protocol in workflow.md) 5e1d115
