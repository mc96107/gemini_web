# Specification: Surgical Removal of Prompt Helper

## Overview
This track involves the complete removal of the "Prompt Helper" feature from the Gemini Termux Agent. The goal is to simplify the codebase by deleting the dedicated prompt-building interface, its associated API routes, and exclusive backend logic, while ensuring that the core "Tree Functionality" (forking, editing, and navigation) in the main chat remains fully functional and unaffected.

## Functional Requirements
- **UI Removal:** Delete the "Prompt Helper" button/entry point from the main chat interface and the Admin UI.
- **API Deletion:** Remove the `app/routers/prompt_helper.py` router and unregister its routes from the FastAPI application.
- **Surgical Service Cleanup:** 
    - Identify and remove methods in `app/services/tree_prompt_service.py` that are *only* used by the Prompt Helper.
    - **CRITICAL:** Retain all methods required for chat forking, history navigation, and tree-based state management in the main chat.
- **Surgical JS Cleanup:**
    - Identify and remove logic in `app/static/tree_helper.js` (or related JS files) that is exclusive to the Prompt Helper UI.
    - **CRITICAL:** Retain all JS logic required for the main chat's tree navigation and fork interactions.
- **Settings Cleanup:** Remove "Prompt Helper" specific configuration options from `data/settings.json` and the Admin Dashboard's "System Instructions" section.
- **Documentation Update:** Remove all descriptions and references to the Prompt Helper from `product.md`, `README.md`, and any other project documentation.

## Non-Functional Requirements
- **Zero Regression:** The main chat's ability to fork conversations and navigate the prompt tree must remain 100% functional.
- **Code Cleanliness:** Remove unused imports and dead code resulting from the deletion.

## Acceptance Criteria
- [ ] The "Prompt Helper" button is no longer visible in the UI.
- [ ] Navigating to `/prompt_helper` (if applicable) returns a 404.
- [ ] The `app/routers/prompt_helper.py` file is deleted.
- [ ] `tree_prompt_service.py` and `tree_helper.js` are leaner but still support main chat forking/navigation.
- [ ] All tests in `tests/test_prompt_helper_api.py` are removed.
- [ ] Remaining tests (especially `tests/test_tree_prompt_service.py`) pass successfully.
- [ ] References to Prompt Helper are removed from `product.md`.

## Out of Scope
- Removal or modification of the core Tree/Forking logic used by the main chat.
- Any changes to other features like "Drive Mode" or "MCP Management".
