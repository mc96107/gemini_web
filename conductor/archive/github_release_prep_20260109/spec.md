# Specification: GitHub Release Preparation & Termux Optimization

## 1. Overview
This track focuses on polishing the `gemini_web` project for a public GitHub release. This involves optimizing the installation script for Android Termux environments, enhancing documentation with visual assets and deployment guides, and resetting the Git history to provide a clean entry point for new users while preserving development history in a separate branch.

## 2. Functional Requirements

### 2.1 Termux Optimization
- **Target File:** `setup_py.sh`
- **Logic Change:** Remove Virtual Environment (`venv`) creation and activation logic.
- **Assumption:** Python is installed globally in the Termux environment. The script should install dependencies directly using `pip`.

### 2.2 Documentation (`README.md`)
- **Installation Guide:** Update instructions to reflect the modified `setup_py.sh` usage.
- **Usage Guide:** Provide clear steps on how to start and use the application.
- **Screenshots:**
    - Use existing images in `screenshots/` directory: `chat.png`, `chat_history.png`, `login.png`, `password.png`, `patterns.png`.
    - Embed these images in the README to showcase the UI.
- **Deployment:** Add a section for serving the application via Nginx Reverse Proxy.
    - **Defaults:** Application on port 8000 (default), Nginx on port 80.
    - Provide a sample Nginx configuration block.

### 2.3 Git Repository Structure
- **History Management:**
    - Move all existing commit history to a new branch named `legacy_history`.
    - Create a fresh `master` branch (orphan) containing the current state of the codebase as a single "Initial Commit".
- **Exclusions:** Ensure `venv/` and other non-essential build artifacts are strictly ignored in `.gitignore` and not included in the clean `master` branch.

## 3. Non-Functional Requirements
- **Cleanliness:** The `master` branch must be free of historical clutter and "work in progress" commits.
- **Clarity:** Documentation must be beginner-friendly.

## 4. Acceptance Criteria
- [ ] `setup_py.sh` installs dependencies globally (for Termux) without errors related to `venv`.
- [ ] `README.md` is comprehensive, including Install, Usage, Screenshots, and Nginx sections.
- [ ] `screenshots/` folder is correctly referenced in the README.
- [ ] Git branch `master` has exactly one commit.
- [ ] Git branch `legacy_history` contains the full previous history.
- [ ] `venv/` directory is not tracked in git.
