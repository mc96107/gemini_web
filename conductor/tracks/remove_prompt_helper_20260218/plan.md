# Implementation Plan: Surgical Removal of Prompt Helper

This plan outlines the steps for the surgical removal of the "Prompt Helper" feature while strictly preserving the core "Tree Functionality" (forking, editing, and navigation) in the main chat.

## Phase 1: Research and Red Phase (TDD)
- [x] Task: **Research Code Usage** 0000000
    - [x] Identify all entry points and dependencies for `app/routers/prompt_helper.py`.
    - [x] Analyze `app/services/tree_prompt_service.py` to distinguish between methods used *only* by Prompt Helper vs. those used by the main chat's tree/forking.
    - [x] Analyze `app/static/tree_helper.js` (and related JS) to identify Prompt Helper-specific UI logic.
- [x] Task: **Verify Core Functionality (Baseline)** 0000000
    - [x] Run existing tests for tree navigation and forking (`tests/test_tree_prompt_service.py`, `tests/test_agent_manager.py`) to ensure a passing baseline.
- [x] Task: **Prepare for Deletion (Red Phase)** 0000000
    - [x] Identify tests in `tests/test_prompt_helper_api.py` and `tests/test_tree_prompt_service.py` that should fail (or be removed) after the feature is gone.
    - [x] Since this is a removal, the "Red Phase" consists of confirming that the feature still exists and then verifying its absence after deletion.

## Phase 2: Backend Removal
- [x] Task: **Remove API Router** 0000000
    - [x] Delete `app/routers/prompt_helper.py`.
    - [x] Unregister the `prompt_helper` router in `app/main.py`.
- [x] Task: **Surgical Service Cleanup** 0000000
    - [x] Remove Prompt Helper-exclusive methods from `app/services/tree_prompt_service.py`.
    - [x] **Verification:** Ensure `tree_prompt_service.py` still supports all methods required by `agent_manager.py` and `chat.py` for forking and navigation.
- [x] Task: **Settings Cleanup** 0000000
    - [x] Remove Prompt Helper-specific settings from `data/settings.json`.
    - [x] Update `app/core/config.py` (if applicable) to remove references to these settings.
- [x] Task: **Conductor - User Manual Verification 'Backend Removal' (Protocol in workflow.md)** 0000000

## Phase 3: Frontend and UI Removal
- [x] Task: **Remove UI Entry Points** 0000000
    - [x] Remove the "Prompt Helper" button/icon from the chat interface templates (e.g., `app/templates/index.html`).
    - [x] Remove Prompt Helper customization options from the Admin Dashboard templates.
- [x] Task: **Surgical JS Cleanup** 0000000
    - [x] Remove Prompt Helper-specific logic from `app/static/tree_helper.js` or related files.
    - [x] **Verification:** Ensure the tree navigation and fork buttons in the main chat history still function correctly.
- [x] Task: **Conductor - User Manual Verification 'Frontend Removal' (Protocol in workflow.md)** 0000000

## Phase 4: Documentation and Final Cleanup
- [x] Task: **Update Project Documentation** 0000000
    - [x] Remove references to Prompt Helper from `product.md`.
    - [x] Remove references from `README.md`.
    - [x] Update any other relevant `.md` files in `conductor/` or the root.
- [x] Task: **Delete Orphaned Tests** 0000000
    - [x] Delete `tests/test_prompt_helper_api.py`.
    - [x] Remove any specific Prompt Helper unit tests from other test files.
- [x] Task: **Final Regression and Verification** 0000000
    - [x] Run the full test suite (`pytest`) to ensure no regressions in core tree functionality.
    - [x] Verify that all "Prompt Helper" references are gone from the UI and codebase.
- [x] Task: **Conductor - User Manual Verification 'Final Cleanup' (Protocol in workflow.md)** 0000000
