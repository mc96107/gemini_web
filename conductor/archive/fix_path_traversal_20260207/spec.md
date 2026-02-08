# Specification - Fix Path Traversal in Uploads Route

## Overview
A security vulnerability was identified in the `/uploads/{filename}` route in `app/main.py`. The current implementation directly joins the user-provided `filename` with the `UPLOAD_DIR`, allowing for potential path traversal attacks (e.g., `../../data/settings.json`) that could expose sensitive project files.

## Functional Requirements
- **Sanitize Input:** The `filename` parameter in the `@app.get("/uploads/{filename}")` route must be sanitized to ensure it only refers to a file within the designated `UPLOAD_DIR`.
- **Method:** Use `pathlib.Path(filename).name` to extract only the filename component, stripping any directory navigation sequences (like `../`).
- **Maintain Compatibility:** Existing valid file retrievals must continue to work without modification.

## Non-Functional Requirements
- **Security:** Ensure that no file outside of `UPLOAD_DIR` can be accessed via this route, even with URL encoding or complex path sequences.
- **Performance:** The sanitization should be computationally inexpensive.

## Acceptance Criteria
- [ ] A request for a valid file in `UPLOAD_DIR` (e.g., `test.png`) returns the file with a `200 OK` status.
- [ ] A request with path traversal sequences (e.g., `../../data/settings.json`) results in a `404 Not Found` (because the sanitized name `settings.json` does not exist in the uploads folder).
- [ ] Encoded traversal sequences (e.g., `%2e%2e%2f`) are handled safely.
- [ ] Automated tests cover successful retrieval, traversal attempts, and 404 behavior for non-existent files.

## Out of Scope
- Implementing a full-blown file management system.
- Modifying upload logic (this fix focuses only on the retrieval/download route).
