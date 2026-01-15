# Specification: Release Documentation Correction

## Overview
Correct the `RELEASE_NOTES.md` to accurately reflect the installation process, clarifying that `setup_release.py` is needed for setting up the environment, or that dependencies must be installed. Also, update the release version tag to v1.1.5 as requested.

## Functional Requirements
- **Update Release Notes:** Modify the "Installation" section of `RELEASE_NOTES.md` to provide correct instructions (run `setup_release.py` first, or manually install deps).
- **Bump Version:** Create a new git tag `v1.1.5`.
- **Update Release:** Update the GitHub release to point to the new tag and use the corrected notes.

## Acceptance Criteria
- [ ] `RELEASE_NOTES.md` correctly explains the installation steps.
- [ ] A new git tag `v1.1.5` exists.
- [ ] The GitHub release is updated/recreated with the new tag and notes.

## Out of Scope
- Code changes to the application logic.
