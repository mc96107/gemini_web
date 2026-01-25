# Implementation Plan - PDF Compression on Upload

This plan implements server-side PDF compression using Ghostscript to optimize file sizes for storage and AI processing, with a graceful fallback if the tool is missing.

## Phase 1: Environment & Discovery [checkpoint: d923661]
- [x] Task: Verify Ghostscript presence in development environment and document installation command for Termux. dd2fc62
- [x] Task: Research and define the exact Ghostscript command-line arguments for `/ebook` preset and file output handling. dd2fc62
- [x] Task: Conductor - User Manual Verification 'Phase 1: Environment & Discovery' (Protocol in workflow.md) dd2fc62

## Phase 2: Core Service Implementation [checkpoint: 61892d9]
- [x] Task: Create `app/services/pdf_service.py` with a `compress_pdf` function. d20f92e
- [x] Task: Write unit tests for `pdf_service.py`. d20f92e
- [x] Task: Conductor - User Manual Verification 'Phase 2: Core Service Implementation' (Protocol in workflow.md) d20f92e

## Phase 3: Integration & UI
- [ ] Task: Integrate `pdf_service` into the file upload pipeline in `app/services/conversion_service.py` or the upload router.
- [ ] Task: Update the `Admin Dashboard` or server logs to show PDF compression statistics (original vs. compressed).
- [ ] Task: Write integration tests for the upload flow with PDF files.
- [ ] Task: Conductor - User Manual Verification 'Phase 3: Integration & UI' (Protocol in workflow.md)

## Phase 4: Finalization
- [ ] Task: Verify end-to-end flow in a Termux-like environment.
- [ ] Task: Ensure documentation (README or a new setup guide) mentions `pkg install ghostscript` for optimal performance.
- [ ] Task: Conductor - User Manual Verification 'Phase 4: Finalization' (Protocol in workflow.md)
