# Implementation Plan - Release Docs Correction

## Phase 1: Update Documentation
- [x] Task: Correct RELEASE_NOTES.md
    - [x] Update the "Installation" section to reference `setup_release.py` or manual `pip install`.
- [x] Task: Create New Tag
    - [x] Run `git tag v1.1.5`.
    - [x] Run `git push origin v1.1.5`.

## Phase 2: Update GitHub Release
- [x] Task: Create/Update Release
    - [x] Use `gh release create v1.1.5 ...` with the updated notes.
    - [x] Mark v1.0.0 as "pre-release" or delete it if preferred (user asked to "update", typically means replacing or creating new). I'll create a new one.
- [x] Task: Conductor - User Manual Verification 'Release Update' (Protocol in workflow.md)
