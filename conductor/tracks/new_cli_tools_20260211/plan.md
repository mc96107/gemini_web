# Plan: Gemini CLI Tool Integration Update

## Phase 1: UI Foundation [checkpoint: fc81f86]
- [x] Task: Update `app/templates/index.html` to include checkboxes for `cli_help`, `ask_user`, and `confirm_output` in the "Read-Only / Safe Tools" section. e63aff2
- [x] Task: Update `app/templates/index.html` to include checkboxes for `activate_skill` and `codebase_investigator` in the "Modification / High-Risk Tools" section. e63aff2
- [ ] Task: Conductor - User Manual Verification 'Phase 1: UI Foundation' (Protocol in workflow.md)

## Phase 2: Verification and Integration [checkpoint: 26186a0]
- [x] Task: Write automated tests in `tests/test_session_tools_integration.py` to verify that the new tools are correctly passed to the Gemini CLI when enabled. 26d4275
- [x] Task: Verify that the frontend correctly loads and saves the state of these new tools via existing API endpoints. 26d4275
- [ ] Task: Conductor - User Manual Verification 'Phase 2: Verification and Integration' (Protocol in workflow.md)