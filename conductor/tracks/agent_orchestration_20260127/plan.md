# Implementation Plan - Agent Orchestration and Linking

This plan outlines the steps to implement a central orchestration system using a root `AGENT.md` file and hierarchical sub-agents linked via Wiki-link style YAML frontmatter.

## Phase 1: Model & Serialization Updates
Update the Agent model to handle orchestration-specific fields and Wiki-link style paths.

- [x] Task: Update `app/models/agent.py`'s `AgentModel` to include:
    - `type`: str (e.g., "Orchestrator", "FunctionAgent")
    - `children`: List[str] (paths in `[[ ]]`)
    - `parent`: Optional[str] (path in `[[ ]]`)
    - `used_by`: List[str] (paths in `[[ ]]`) [a397f28]
- [x] Task: Enhance `from_markdown` and `to_markdown` in `AgentModel` to parse and serialize Wiki-links (`[[path]]`) specifically for these fields. [a397f28]
- [x] Task: Add unit tests for Wiki-link parsing and orchestration field serialization. [a397f28]
- [ ] Task: Conductor - User Manual Verification 'Phase 1: Model & Serialization Updates' (Protocol in workflow.md)

## Phase 2: Orchestrator Management & Linking Logic
Implement the backend logic for managing the root orchestrator and the linking process.

- [ ] Task: Update `AgentManager` to handle the root `AGENT.md` file (which sits at project root, outside the `data/agents` directory).
- [ ] Task: Implement `AgentManager.initialize_root_orchestrator()` to create a default root `AGENT.md` if it doesn't exist.
- [ ] Task: Implement `AgentManager.set_agent_enabled(category, folder_name, enabled: bool)`:
    - If `True`: Add sub-agent path to root `children`, set sub-agent `parent` to `[[AGENT.md]]`, and update `used_by`.
    - If `False`: Remove sub-agent path from root `children`, clear sub-agent `parent`, and update `used_by`.
- [ ] Task: Implement `AgentManager.validate_orchestration()`:
    - Check if all agents in the root's `children` list are actually referenced by name or path within the root's prompt string.
- [ ] Task: Write integration tests for the enabling/disabling logic and orchestration validation.
- [ ] Task: Conductor - User Manual Verification 'Phase 2: Orchestrator Management & Linking Logic' (Protocol in workflow.md)

## Phase 3: Admin UI Enhancements
Update the Admin Web UI to expose orchestration controls and validation feedback.

- [ ] Task: Add an "Enabled" toggle (switch) to each row in the Agent Management table in `app/templates/admin.html`.
- [ ] Task: Create new API endpoints in `app/routers/admin.py`:
    - `POST /admin/agents/{category}/{name}/toggle-enabled`: Calls the toggle logic.
    - `GET /admin/agents/validate`: Returns orchestration validation results (warnings).
- [ ] Task: Implement JavaScript logic to handle the toggle and refresh the UI state.
- [ ] Task: Add a UI warning banner or icon if `validate_orchestration` returns errors/warnings.
- [ ] Task: Verify mobile responsiveness for the new toggle.
- [ ] Task: Conductor - User Manual Verification 'Phase 3: Admin UI Enhancements' (Protocol in workflow.md)