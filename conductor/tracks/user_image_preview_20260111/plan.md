# Implementation Plan - User Message Image Preview

## Phase 1: Infrastructure and UI Logic
- [x] Task: Serve Uploaded Attachments 465c7dd
    - [x] Add a route or mount `UPLOAD_DIR` in `app/main.py` to serve files to the browser.
    - [x] Route should be something like `/uploads/{filename}`.
- [ ] Task: Implement Image Preview Logic in `app/static/script.js`
    - [ ] Update `createMessageDiv` to detect image attachments.
    - [ ] For new uploads: Use `URL.createObjectURL(file)` to show an immediate thumbnail.
    - [ ] For history: Parse strings like `@tmp/user_attachments/filename` and convert them to the new serving URL.
    - [ ] Insert an `<img>` tag with a class like `message-thumbnail`.
- [ ] Task: Add Styling and Interaction
    - [ ] Add CSS to `app/static/style.css` for `.message-thumbnail` (max-width: 150px, border-radius, cursor: pointer).
    - [ ] Add a click listener to thumbnails to open the full image in a new tab.
- [ ] Task: Conductor - User Manual Verification 'Infrastructure and UI Logic' (Protocol in workflow.md)

## Phase 2: Verification
- [ ] Task: Verify Immediate Preview
    - [ ] Upload an image and confirm the thumbnail appears correctly in the user bubble.
- [ ] Task: Verify History Preview
    - [ ] Refresh the page/switch sessions and confirm that historical images also display thumbnails.
- [ ] Task: Verify Full Image View
    - [ ] Click a thumbnail and confirm the full-sized image opens as expected.
- [ ] Task: Conductor - User Manual Verification 'Verification' (Protocol in workflow.md)
