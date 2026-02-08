# Specification: Fix Historical Interactive Question Rendering

## Overview
When a user reloads a chat session or logs back in, messages that were originally rendered as "Structured Interactive Questioning" cards (Question Cards) are displayed as raw JSON blocks instead of interactive UI components. This breaks the user experience and makes it difficult to follow previous decision points.

## Functional Requirements
- **Automatic Rendering:** Upon loading chat history (via initial state or scrolling/pagination), any message containing structured questioning data must be detected and transformed into the appropriate interactive card component.
- **State Persistence:** The rendered cards should reflect their previous state (e.g., if already answered, they should ideally show the selected answer or be disabled, consistent with current session behavior).
- **Consistency:** The visual styling and interaction of reloaded cards must match the cards generated during a live session.

## Non-Functional Requirements
- **Performance:** Rendering historical cards should not significantly delay the initial chat load or scrolling performance.
- **Robustness:** The rendering logic should gracefully handle malformed or unexpected JSON data without crashing the chat interface.

## Acceptance Criteria
- [ ] Load a chat containing historical interactive questions: cards render as UI elements, not raw JSON.
- [ ] Refresh the page on an active chat with questions: cards maintain their interactive rendering.
- [ ] Verify that interactive elements (buttons/inputs) are present in the reloaded cards.

## Out of Scope
- Modifying the underlying data format for Question Cards.
- Changing the behavior of how questions are *generated* by the AI.
