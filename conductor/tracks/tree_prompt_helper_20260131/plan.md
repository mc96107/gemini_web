# Implementation Plan: Tree Prompt Helper (Visual)

## Phase 1: Backend Infrastructure & State Management [checkpoint: 2fcd1d9]
- [x] Task: Create `prompts/` directory for finalized prompts. 24ee13c
    - [ ] Add `prompts/` to `.gitignore`.
- [x] Task: Define `PromptTreeSession` Pydantic model in a new service file. 6504ec8
    - [ ] `nodes`: List of question/answer objects with hierarchical links.
    - [ ] `current_node_id`: Track current position in the tree.
- [x] Task: Implement `TreePromptService` in `app/services/tree_prompt_service.py`. d4d542f
    - [ ] Logic for adding nodes, rewinding, and synthesizing the final prompt from gathered facts.
- [x] Task: Conductor - User Manual Verification 'Phase 1: Backend Infrastructure & State Management' (Protocol in workflow.md) 2fcd1d9

## Phase 2: Agent Logic & API Endpoints [checkpoint: 31c4ec9]
- [x] Task: Implement specialized LLM prompt logic for the Tree Helper. 1453c0b
    - [ ] Logic to enforce structured output (e.g., JSON containing the question and suggested options).
- [x] Task: Create `app/routers/prompt_helper.py` and register it in `app/main.py`. 7591c80
    - [ ] `GET /api/prompt-helper/session`: Get current tree state.
    - [ ] `POST /api/prompt-helper/start`: Initialize a new guided session.
    - [ ] `POST /api/prompt-helper/answer`: Submit answer and get next question.
    - [ ] `POST /api/prompt-helper/rewind`: Rewind session to a specific node.
    - [ ] `POST /api/prompt-helper/save`: Synthesize and save final prompt to `prompts/`.
- [x] Task: Conductor - User Manual Verification 'Phase 2: Agent Logic & API Endpoints' (Protocol in workflow.md) 31c4ec9

## Phase 3: Frontend UI - Tree Visualization & Integration [checkpoint: 18f7a48]
- [x] Task: Create `static/tree_helper.js`. c6fedf8
    - [ ] Implement a `PromptTreeView` class using vanilla JS and CSS.
    - [ ] Use a collapsible nested list structure for the tree representation.
- [x] Task: Update `static/style.css`. c6fedf8
    - [ ] Add styles for tree nodes, active path, and "rewind" interaction states.
- [x] Task: Update `templates/index.html`. c6fedf8
    - [ ] Add container for the tree view (sidebar or toggleable panel).
    - [ ] Add "Prompt Helper" mode toggle in the main interface.
- [x] Task: Conductor - User Manual Verification 'Phase 3: Frontend UI - Tree Visualization & Integration' (Protocol in workflow.md) 18f7a48

## Phase 4: Frontend UI - Dynamic Inputs & Interaction
- [ ] Task: Enhance input rendering logic to handle dynamic fields.
    - [ ] Render buttons when `suggested_options` are present.
    - [ ] Render standard text input otherwise.
- [ ] Task: Wire up tree node clicks to trigger the rewind API.
- [ ] Task: Implement real-time synchronization between chat messages and the tree view.
- [ ] Task: Conductor - User Manual Verification 'Phase 4: Frontend UI - Dynamic Inputs & Interaction' (Protocol in workflow.md)

## Phase 5: Refinement, Persistence & Polish
- [ ] Task: Implement the "Review & Save" flow.
    - [ ] Final review modal for the synthesized prompt.
    - [ ] Success notification upon saving to `prompts/`.
- [ ] Task: Add mobile-specific optimizations (responsive tree view, touch targets).
- [ ] Task: Final end-to-end testing and code coverage verification.
- [ ] Task: Conductor - User Manual Verification 'Phase 5: Refinement, Persistence & Polish' (Protocol in workflow.md)