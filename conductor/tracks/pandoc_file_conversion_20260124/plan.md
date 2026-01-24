# Implementation Plan: Pandoc File Conversion

## Phase 1: Environment Setup & Tooling [checkpoint: 3490833]
- [x] Task: Verify Pandoc availability on the system and update `requirements.txt` if a wrapper like `pypandoc` is chosen. 150079c
- [x] Task: Update `tech-stack.md` to include Pandoc as a document processing tool. 150079c
- [x] Task: Conductor - User Manual Verification 'Phase 1: Environment Setup'

## Phase 2: Conversion Service [checkpoint: 3cb79fe]
- [x] Task: Implement `FileConversionService` in `app/services/conversion_service.py` to handle Pandoc logic. 2cc903d
- [x] Task: Write Tests: Verify `.docx` to `.md` conversion strips images. 2cc903d
- [x] Task: Write Tests: Verify `.xlsx` to `.md` conversion produces readable tables. 2cc903d
- [x] Task: Conductor - User Manual Verification 'Phase 2: Conversion Service'

## Phase 3: Router Integration
- [ ] Task: Update `app/routers/chat.py` to route uploaded `.docx`/`.xlsx` files through the conversion service.
- [ ] Task: Ensure the `GeminiAgent` receives the path to the converted `.md` file.
- [ ] Task: Write Tests: Integration test for full upload-convert-send flow.
- [ ] Task: Conductor - User Manual Verification 'Phase 3: Router Integration'

## Phase 4: Error Handling & Cleanup
- [ ] Task: Implement robust error handling for failed conversions (e.g., corrupted files, missing Pandoc).
- [ ] Task: Ensure temporary converted files are managed/cleaned up correctly.
- [ ] Task: Conductor - User Manual Verification 'Phase 4: Final Verification'
