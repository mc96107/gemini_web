# Track Specification: Agent Orchestration and Linking

## Overview
This track implements an orchestration system where a central `AGENT.md` file at the project root manages a list of "Enabled" sub-agents. Relationships are maintained using YAML frontmatter with Wiki-link style paths (`[[path/to/AGENT.md]]`).

## Functional Requirements
- **Root Orchestrator:**
    - A file named `AGENT.md` MUST exist at the project root.
    - Frontmatter MUST include `type: Orchestrator` and a `children` list.
    - Example: `children: [[data/agents/functions/fabric/AGENT.md]]`.
- **Sub-Agent Structure:**
    - Sub-agents (in `data/agents/`) MUST include `type: FunctionAgent` (or similar) in their frontmatter.
    - MUST include `parent: [[AGENT.md]]` when enabled.
    - MUST include `used_by: [...]` to automatically track which systems/agents are using them.
- **Admin UI Enhancements:**
    - **Enabled Toggle:** Add a toggle switch to each agent in the Admin UI list.
    - **Linking Logic:**
        - Toggling "On" adds the sub-agent's relative path to the root `AGENT.md`'s `children` list and sets the sub-agent's `parent` field.
        - Toggling "Off" removes these links.
    - **Wiki-link Format:** All links in frontmatter MUST use the `[[relative/path]]` format.
- **Automatic Tracking:** The `used_by` field in sub-agents should be updated automatically when linked/unlinked by an orchestrator.
- **Orchestration Validation:**
    - The root `AGENT.md` prompt MUST reference the child agents it manages (e.g., dynamically injecting descriptions or names).
    - If a child is added to `children` but NOT referenced in the prompt, display a warning in the UI.

## Non-Functional Requirements
- **Atomic Updates:** Ensure that when an agent is enabled/disabled, both the root `AGENT.md` and the sub-agent's `AGENT.md` are updated consistently.
- **Path Resolution:** Correctly handle relative paths from the project root.

## Acceptance Criteria
- [ ] Root `AGENT.md` is initialized with correct boilerplate if missing.
- [ ] Admin can enable/disable sub-agents via a toggle in the UI.
- [ ] Enabling an agent correctly updates `children` in root and `parent`/`used_by` in the sub-agent.
- [ ] Disabling an agent removes the corresponding links from both files.
- [ ] Frontmatter parsing and serialization support the `[[ ]]` Wiki-link format.
- [ ] UI displays a warning if an enabled agent is not referenced in the Orchestrator's prompt.

## Out of Scope
- Support for multiple orchestrators (only the one at the project root is supported).