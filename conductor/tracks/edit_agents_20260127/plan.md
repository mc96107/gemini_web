# Implementation Plan - Edit agents from admin webui

This plan outlines the steps to implement a hierarchical agent management system within the Admin UI, using `AGENT.md` files with YAML frontmatter.

## Phase 1: Foundation & Backend Setup [checkpoint: ba7ed45]
Setup the directory structure, configuration, and core service for managing AGENT.md files.

- [x] Task: Define AGENT_BASE_DIR in `app/core/config.py` (pointing to a configurable path, defaulting to a directory like `data/agents`). cbba867
- [x] Task: Create `app/models/agent.py` to define the `AgentModel` schema (Metadata + Content). 2c7cfc5
- [x] Task: Implement `app/services/agent_manager.py` with methods to:
    - List all agents (recursively scanning directories).
    - Read an `AGENT.md` (parsing YAML frontmatter and body).
    - Save/Update an `AGENT.md` (serializing frontmatter and body).
    - Delete an agent folder.
    5a4bf17
- [x] Task: Write unit tests for `agent_manager.py` (mocking filesystem). 5a4bf17
- [x] Task: Conductor - User Manual Verification 'Phase 1: Foundation & Backend Setup' (Protocol in workflow.md) ba7ed45

## Phase 2: API & Admin Router Integration
Expose the agent management functionality through FastAPI endpoints.

- [x] Task: Add new routes to `app/routers/admin.py`:
    - `GET /admin/agents`: Returns JSON list of all agents and categories.
    - `GET /admin/agents/{category}/{name}`: Returns agent details.
    - `POST /admin/agents`: Create or update an agent.
    - `DELETE /admin/agents/{category}/{name}`: Delete an agent.
    da2a103
- [x] Task: Implement a helper to initialize the default `functions/fabric/AGENT.md` if it doesn't exist. da2a103
- [x] Task: Write integration tests for the new admin API endpoints. da2a103
- [ ] Task: Conductor - User Manual Verification 'Phase 2: API & Admin Router Integration' (Protocol in workflow.md)

## Phase 3: Admin Web UI Implementation
Build the frontend interface for managing agents within the existing admin template.

- [ ] Task: Update `app/templates/admin.html` (or create a partial) to include an "Agents" management section.
- [ ] Task: Implement the "Flat List with Filtering" UI using JavaScript in `admin.html`.
- [ ] Task: Create a modal or dedicated view for the Agent Editor (Name, Description, and a textarea for the System Prompt).
- [ ] Task: Add client-side validation for category and folder names (sanitization).
- [ ] Task: Verify the UI responsiveness and category filtering on mobile.
- [ ] Task: Conductor - User Manual Verification 'Phase 3: Admin Web UI Implementation' (Protocol in workflow.md)