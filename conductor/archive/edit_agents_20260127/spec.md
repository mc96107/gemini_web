# Track Specification: Edit agents from admin webui

## Overview
This track introduces a specialized "Agent" management system within the Admin UI. It moves beyond the simple "Patterns" system by implementing an orchestrator-style structure where agents are defined by `AGENT.md` files stored in a hierarchical directory structure.

## Functional Requirements
- **Hierarchical Storage:** Agents are stored in subfolders categorized by type (e.g., `functions/`, `projects/`, `systems/`). Each agent has its own folder containing an `AGENT.md` file.
- **Markdown with Frontmatter:** `AGENT.md` files must use YAML frontmatter for metadata (Name, Description) and the Markdown body for the System Instructions (Prompt).
- **Admin Management UI:**
    - **Flat List View:** Display all agents in a single list with category-based filtering.
    - **CRUD Operations:** Ability to create, read, update, and delete agents and their corresponding folders/files.
    - **Live Editor:** A Markdown editor (textarea or similar) in the Admin UI to modify the `AGENT.md` content.
- **Pattern Integration:** A dedicated sub-agent (e.g., `functions/fabric/AGENT.md`) should be created to bridge the new Agent system with the existing Patterns prompts.
- **Independent Orchestrator:** This system is architecturally distinct from the existing `PATTERNS` system in `app/core/patterns.py`.

## Non-Functional Requirements
- **File System Safety:** Ensure proper sanitization of folder and file names to prevent directory traversal or invalid paths.
- **Concurrency:** Handle file locking or simple "last-write-wins" to prevent corruption if multiple admin actions occur.

## Acceptance Criteria
- [ ] Admin can view a list of all agents filtered by category.
- [ ] Admin can create a new agent (specifying category, subfolder name, and content).
- [ ] Admin can edit an existing agent's frontmatter (name/desc) and system prompt.
- [ ] Admin can delete an agent (removing the folder and `AGENT.md`).
- [ ] `AGENT.md` files are correctly saved with YAML frontmatter and Markdown body.
- [ ] The `functions/fabric` agent exists and is initialized.

## Out of Scope
- Runtime execution of the "Orchestrator" logic (this track focuses on the *management* of agent definitions).
- Complex model-specific settings (temperature, top-p) beyond what is defined in the frontmatter.