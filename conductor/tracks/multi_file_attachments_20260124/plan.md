# Implementation Plan: Ability to Attach Multiple Files

## Phase 1: Frontend Infrastructure & Multi-File Selection
This phase focuses on updating the UI to support selecting multiple files and managing them in a queue.

- [x] Task: Update chat UI template to support multiple file selection in input and add drag-and-drop overlay. 4249cb6
- [ ] Task: Implement `AttachmentManager` JavaScript class to handle the queue, size limits, and removal logic.
- [ ] Task: Write Tests: Verify `AttachmentManager` correctly adds/removes files and calculates cumulative size.
- [ ] Task: Implement: `AttachmentManager` logic for queue management and size validation alerts.
- [ ] Task: Conductor - User Manual Verification 'Phase 1: Frontend Infrastructure' (Protocol in workflow.md)

## Phase 2: Integrated Compression & Previews
Integrate existing compression logic with the multi-file queue and implement visual previews.

- [ ] Task: Write Tests: Verify images added to the queue are compressed and produce valid previews.
- [ ] Task: Implement: Hook `AttachmentManager` into existing `compression.js` for automatic processing.
- [ ] Task: Implement: UI components for the attachment queue (thumbnails, file icons, and delete buttons).
- [ ] Task: Conductor - User Manual Verification 'Phase 2: Integrated Compression' (Protocol in workflow.md)

## Phase 3: Backend Integration & Send Logic
Update the message sending logic to handle multiple files and ensure the backend correctly processes the multipart request.

- [ ] Task: Update `script.js` `sendMessage` function to iterate through the `AttachmentManager` queue and append all files to `FormData`.
- [ ] Task: Write Tests: Verify `chat.py` router correctly receives and handles multiple files in a single request.
- [ ] Task: Implement: Backend adjustments (if any) in `llm_service.py` to process multiple attachments per message.
- [ ] Task: Conductor - User Manual Verification 'Phase 3: Backend Integration' (Protocol in workflow.md)

## Phase 4: Final Polishing & Mobile Verification
Refine the UI for mobile devices and perform final integration testing.

- [ ] Task: Style the attachment queue and drag-and-drop zone for mobile responsiveness (Bootstrap 5).
- [ ] Task: Write Tests: End-to-end integration test for the full multi-file upload flow.
- [ ] Task: Conductor - User Manual Verification 'Phase 4: Final Polishing' (Protocol in workflow.md)
