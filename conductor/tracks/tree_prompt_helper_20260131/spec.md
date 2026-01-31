# Specification: Tree Prompt Helper (Visual)

## Overview
Implement a "Tree Prompt Helper" feature that allows users to build complex prompts through a guided, interactive questioning process. The feature will visualize the prompt's evolution as a collapsible tree structure, allowing users to track their progress, revisit previous decisions, and refine the final output before it is generated or saved.

## Functional Requirements
- **Guided Interaction**: The system will act as an agent that asks targeted questions to gather information for a high-quality prompt.
- **Dynamic Inputs**: Support for both buttons (multiple-choice) and text input fields, determined dynamically by the LLM's response (e.g., presence of suggested options).
- **Visual Tree View**: A collapsible, nested tree structure (file-explorer style) representing the hierarchy of gathered information and user responses.
- **Rewind/Branching Logic**: Users can click on any previous node in the tree to re-answer that question. This action "rewinds" the state to that point, allowing users to explore different prompt directions (branching).
- **Edit & Refine**: Users can review and modify the gathered facts before final agreement.
- **Persistence**: Finalized prompts will be saved in a `prompts/` directory.
    - Filename format: `prompt_<timestamp>_<summary_title>.txt` (or .md).
    - Content: The synthesized final prompt text.
- **Entry Point**: A dedicated "Mode" or "Agent" selectable within the application UI (e.g., via sidebar or mode toggle).

## Non-Functional Requirements
- **UI Consistency**: Use existing styling (Bootstrap/Material Design principles) and ensure the tree view is responsive.
- **Low Latency**: Tree updates and state transitions should feel snappy and provide clear loading indicators.

## Acceptance Criteria
- [ ] User can enter "Tree Prompt Helper" mode.
- [ ] The system presents questions and handles both button and text replies.
- [ ] The visual tree correctly updates with each interaction.
- [ ] Clicking a previous node successfully rewinds the session state.
- [ ] The final prompt is synthesized and displayed for review.
- [ ] Saving the prompt creates a file in the `prompts/` folder with the correct naming convention.

## Out of Scope
- Multi-user collaborative prompt building.
- Exporting the tree visualization as an image.
- Integration with external (non-Gemini) LLM providers for this specific feature.