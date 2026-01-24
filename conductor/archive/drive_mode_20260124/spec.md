# Specification: Drive Mode (Voice-Only Loop)

## Overview
Implement a hands-free "Drive Mode" for the Gemini Termux Agent PWA. This feature enables a continuous "Conversation Loop": the app listens for user speech, sends it to the AI, reads the AI's response aloud, and immediately begins listening again. This is designed for eyes-free/hands-free use cases like driving.

## Functional Requirements
- **Drive Mode Toggle**: Add a button to the UI to start and stop the "Drive Mode" loop.
- **State 1: Listening**: Use the Web Speech API (`webkitSpeechRecognition`) to transcribe user voice to text in real-time.
- **State 2: Processing**: When the user stops speaking, automatically send the transcribed text to the existing Python backend.
- **State 3: Speaking**: Use the Web Speech API (`speechSynthesis`) to read the AI's response aloud.
- **State 4: Looping**: Immediately trigger the "Listening" state once the AI finishes speaking.
- **Visual Feedback**: Display clear UI indicators for "Listening", "Processing", and "Speaking" states.
- **Wake-Lock Integration**: Request a screen wake-lock while Drive Mode is active to prevent the device from sleeping and interrupting the loop.
- **Silence Management**: The system should remain in the "Listening" state if no speech is detected, rather than timing out the entire loop.

## Non-Functional Requirements
- **Browser Compatibility**: Drive Mode will only be available in browsers that fully support the required Web Speech APIs (primarily Chrome on Android).
- **Graceful Error Handling**: If voice recognition or network errors persist, the loop should stop automatically to prevent unstable behavior.

## Acceptance Criteria
- [ ] The "Drive Mode" button is visible only in compatible browsers.
- [ ] Tapping "Start Drive Mode" successfully initiates the loop and requests a wake-lock.
- [ ] The app correctly transitions from Listening -> Sending -> Speaking -> Listening without user intervention.
- [ ] AI responses are clearly audible via the device's default TTS engine.
- [ ] Tapping "Stop Drive Mode" or the global "Stop" button breaks the loop and releases the wake-lock.
- [ ] The UI clearly indicates the current state of the voice loop.

## Out of Scope
- Background operation when the PWA is minimized or the screen is manually turned off (due to browser security constraints).
- Support for non-Web Speech API browsers (e.g., Brave/Firefox) for the full automated loop.
