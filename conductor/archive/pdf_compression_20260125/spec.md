# Specification - PDF Compression on Upload

## Overview
This track implements server-side PDF compression for all PDF files uploaded through the chat interface. By utilizing Ghostscript, the application will automatically optimize PDFs to reduce file size while maintaining readability for both the user and the Gemini model.

## Functional Requirements
- **Server-Side Compression:** Automatically compress PDF attachments upon upload before they are stored or processed.
- **Ghostscript Integration:** Use the Ghostscript CLI via Python's `subprocess` to perform the compression.
- **Default Quality:** Apply the `/ebook` (150 dpi) Ghostscript preset to balance file size and visual/OCR clarity.
- **Graceful Fallback:** 
    - Detect if Ghostscript is installed in the Termux environment.
    - If Ghostscript is missing, log a warning and proceed with the original uncompressed file to ensure the upload doesn't fail.
- **Optimization Reporting:** (Internal) Log the original size vs. the compressed size for monitoring efficiency.

## Non-Functional Requirements
- **Maintainability:** Ensure the Ghostscript command is configurable or easily accessible in the code for future adjustments to compression levels.
- **Security:** Sanitize filenames before passing them to the shell command to prevent command injection.

## Acceptance Criteria
- [ ] Uploading a PDF triggers the compression logic.
- [ ] If Ghostscript is installed, the resulting file is smaller than the original (assuming it wasn't already optimized).
- [ ] If Ghostscript is NOT installed, the file is still uploaded and usable in its original state.
- [ ] The Gemini model can successfully read and analyze text/images within the compressed PDF.

## Out of Scope
- Client-side PDF compression.
- Support for compressing encrypted or password-protected PDFs (these will remain uncompressed).
- User-selectable compression levels in the UI (hardcoded to 'Ebook' for now).
