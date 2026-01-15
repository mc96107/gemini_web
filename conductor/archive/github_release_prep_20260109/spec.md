# Specification: GitHub Release Creation

## Overview
Automate the process of creating a new GitHub release. This involves determining the next version number, generating release notes based on recent changes, building the single-file release artifact, and publishing it all to GitHub using the `gh` CLI.

## Functional Requirements
- **Version Management:** Determine the next semantic version number (e.g., v1.0.1 -> v1.0.2).
- **Artifact Generation:** Ensure `gemini_agent_release.py` is up-to-date by running `scripts/recombine.py`.
- **Release Notes:** Generate comprehensive release notes summarizing changes since the last release.
- **Publication:** Use `gh release create` to publish the release with the artifact and notes.

## Acceptance Criteria
- [ ] A new release is created on GitHub.
- [ ] The release includes `gemini_agent_release.py` as an asset.
- [ ] Release notes accurately reflect recent features and fixes (Image Preview, Compression, etc.).
- [ ] The git tag corresponds to the new version number.

## Out of Scope
- CI/CD pipeline integration (this is a manual CLI-driven release).
