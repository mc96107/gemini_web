# Specification: Infinite Scroll & UI Improvements

## Overview
Improve the user experience by replacing the manual "Load Older Messages" button with an infinite scroll mechanism. Additionally, ensure the copy button is always accessible (sticky) and optimize the interface for a "lighter" feel.

## Functional Requirements
- **Infinite Scroll:** Automatically load older messages when the user scrolls to the top of the chat container.
- **Scroll Position:** Maintain the user's scroll position when new messages are loaded (don't jump to top).
- **Sticky Copy Button:** The copy button on message bubbles should remain visible or be easily accessible, potentially sticking to the corner of the bubble.

## Acceptance Criteria
- [ ] Scrolling to the top triggers message loading.
- [ ] "Load More" button is removed/hidden.
- [ ] Scroll position stays stable during loading.
- [ ] Copy button is styled to be persistent/accessible.

## Out of Scope
- React migration (staying with Vanilla JS).
