# Specification: Git Publishing Setup

## 1. Overview
Prepare the repository for public publishing by segregating the development history (containing sensitive information) from a clean, public-facing branch.

## 2. Goals
*   Preserve existing history in a private branch.
*   Create a new `master` branch with no sensitive files (like `original_app.py` or old `py.py`) in its history.

## 3. Implementation
*   Rename current branch to `private-dev`.
*   Create an orphaned `master` branch and import cleaned files.
