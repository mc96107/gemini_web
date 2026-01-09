# Plan: GitHub Release Preparation & Git History Reset

This plan outlines the steps to optimize the project for Termux, update the documentation with existing screenshots and deployment guides, and perform a clean Git history reset for the public release.

## Phase 1: Code & Documentation Updates [checkpoint: ccb40f6]
- [x] Task: Modify `setup_py.sh` to remove `venv` creation/activation and install dependencies globally. 1b7ffbb
- [x] Task: Update `README.md` with:
    - [x] New Termux installation instructions.
    - [x] Comprehensive usage guide.
    - [x] Nginx Reverse Proxy configuration guide (port 8000 -> 80).
    - [x] Embedded screenshots from the `screenshots/` directory. 6701573
- [x] Task: Conductor - User Manual Verification 'Phase 1: Code & Documentation Updates' (Protocol in workflow.md) e515ba8

## Phase 2: Git History Reset & Repository Cleanup [checkpoint: 5f0aa4b]
- [x] Task: Verify `.gitignore` strictly excludes `venv/` and other local artifacts. cd72bde
- [x] Task: Create a new branch `legacy_history` from the current `master`.
- [x] Task: Reset the `master` branch:
    - [x] Create an orphan `master` branch.
    - [x] Stage all current files (excluding ignored ones).
    - [x] Commit with message "Initial commit for public release". cd72bde
- [x] Task: Verify the repository state (clean master with 1 commit, full history in legacy_history). cd72bde
- [x] Task: Conductor - User Manual Verification 'Phase 2: Git History Reset & Repository Cleanup' (Protocol in workflow.md) c776089

## Phase 3: Final Verification [checkpoint: 1f36368]
- [x] Task: Run a test installation using the modified `setup_py.sh` (simulated or verified by script content). 1d7e301
- [x] Task: Final review of `README.md` rendering and links. 1d7e301
- [x] Task: Conductor - User Manual Verification 'Phase 3: Final Verification' (Protocol in workflow.md) 1d7e301
