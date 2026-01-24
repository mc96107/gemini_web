# Implementation Plan: Drive Mode (Voice-Only Loop)

## Phase 1: Infrastructure & Browser Compatibility [checkpoint: b2431f9]
Establish the foundational state management for Drive Mode and implement detection for supported browsers.

- [x] Task: Create `DriveModeManager` class in `app/static/drive_mode.js` to manage loop state and browser capability checks. e9b943d
- [x] Task: Implement `isSupported()` method to check for `webkitSpeechRecognition` and `speechSynthesis`. e9b943d
- [x] Task: Write unit tests in `tests/drive_mode.test.js` verifying compatibility detection logic. e9b943d
- [x] Task: Conductor - User Manual Verification 'Phase 1: Infrastructure & Browser Compatibility' (Protocol in workflow.md) b2431f9

## Phase 2: UI Integration & Wake-Lock
Add the Drive Mode controls to the chat interface and implement screen wake-lock functionality.

- [x] Task: Add "Drive Mode" toggle button to the chat input area in `app/templates/index.html`. [commit: b2431f9]
- [x] Task: Implement button visibility logic to hide it on unsupported browsers. [commit: b2431f9]
- [x] Task: Implement Wake-Lock API integration in `DriveModeManager` to keep the screen on during active loops. [commit: b2431f9]
- [~] Task: Write tests in `tests/test_multi_file_ui.py` (or a new UI test file) to verify the button appears/disappears correctly based on browser capabilities.
- [ ] Task: Conductor - User Manual Verification 'Phase 2: UI Integration & Wake-Lock' (Protocol in workflow.md)

## Phase 3: The Conversation Loop (STT & TTS)
Implement the core logic of the hands-free loop using Web Speech APIs.

- [ ] Task: Implement "Listening" state (STT) using `webkitSpeechRecognition` with automatic "end-of-speech" detection.
- [ ] Task: Implement "Speaking" state (TTS) using `speechSynthesis` to read back AI responses.
- [ ] Task: Implement the loop logic: transition from STT result -> Send Message -> TTS start -> TTS end -> STT restart.
- [ ] Task: Implement visual state indicators (Listening/Processing/Speaking) in the UI.
- [ ] Task: Write integration tests in `tests/test_drive_mode_loop.py` (mocking Web Speech APIs) to verify state transitions.
- [ ] Task: Conductor - User Manual Verification 'Phase 3: The Conversation Loop (STT & TTS)' (Protocol in workflow.md)

## Phase 4: Error Handling & Refinement
Ensure the loop is robust against network issues, silence, and manual interruptions.

- [ ] Task: Implement error handling: retry logic for STT and automatic loop termination on persistent failures.
- [ ] Task: Implement silence management: ensure the loop stays in "Listening" if no speech is detected.
- [ ] Task: Implement manual stop override to break the loop via the toggle or global "Stop" button.
- [ ] Task: Final code review and cleanup of `app/static/drive_mode.js` and `app/static/script.js`.
- [ ] Task: Conductor - User Manual Verification 'Phase 4: Error Handling & Refinement' (Protocol in workflow.md)
