# Implementation Plan - Fix Path Traversal in Uploads Route

## Phase 1: Verification & TDD Setup [checkpoint: 299ac3a]
- [x] Task: Create a reproduction test suite for the path traversal vulnerability. [417b585]
    - [x] Create `tests/test_path_traversal.py`.
    - [x] Implement a test case that attempts to access `data/settings.json` via `/uploads/../../data/settings.json`.
    - [x] Implement a test case for URL-encoded traversal (`%2e%2e%2f`).
    - [x] Verify these tests FAIL (Red Phase).
- [x] Task: Conductor - User Manual Verification 'Phase 1: Verification & TDD Setup' (Protocol in workflow.md) [417b585]

## Phase 2: Implementation & Green Phase
- [ ] Task: Implement filename sanitization in the uploads route.
    - [ ] Modify `@app.get("/uploads/{filename}")` in `app/main.py`.
    - [ ] Import `pathlib`.
    - [ ] Update `fpath` calculation to use `pathlib.Path(filename).name`.
- [ ] Task: Verify the fix with the test suite.
    - [ ] Run `tests/test_path_traversal.py` and confirm all tests pass (Green Phase).
    - [ ] Run existing `tests/test_uploads.py` to ensure no regressions.
- [ ] Task: Conductor - User Manual Verification 'Phase 2: Implementation & Green Phase' (Protocol in workflow.md)

## Phase 3: Final Validation & Cleanup
- [ ] Task: Execute full test suite and check coverage.
    - [ ] Run all project tests.
    - [ ] Verify coverage for `app/main.py` is >80%.
- [ ] Task: Conductor - User Manual Verification 'Phase 3: Final Validation & Cleanup' (Protocol in workflow.md)
