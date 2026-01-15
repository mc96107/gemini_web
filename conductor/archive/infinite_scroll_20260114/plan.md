# Implementation Plan - Infinite Scroll & UI

## Phase 1: Infinite Scroll
- [x] Task: Setup Intersection Observer
    - [x] Add a sentinel element at the top of `#chat-container` in `index.html`.
    - [x] In `script.js`, use `IntersectionObserver` to trigger `loadMessages` when the sentinel comes into view.
- [x] Task: Adjust Scroll Logic
    - [x] Update `loadMessages` to calculate and restore scroll position after prepending messages.

## Phase 2: UI Polish
- [x] Task: Sticky Copy Button
    - [x] Update `style.css` to position the `.copy-btn` absolutely within the relative `.message` container, ensuring it stays in the top-right corner. (Already mostly done, verify "sticky" behavior if message is long - `position: sticky` might be needed if the bubble is very tall).
    - [x] Ensure it doesn't overlap text.
- [x] Task: Conductor - User Manual Verification 'Infinite Scroll & UI' (Protocol in workflow.md)
