# Plan - Fork Enhancements (Permissions & Branding)

This plan outlines the steps to implement tool permission and tag inheritance for forked chats, and to update the fork icon across the UI.

## Phase 1: Inheritance Logic (Backend)
Implementation of the data transfer logic when a chat is cloned.

- [x] Task: Create reproduction test for tool/tag inheritance 443c4b3
- [x] Task: Implement Tool Permission Inheritance 443c4b3
- [x] Task: Implement Tag Inheritance 443c4b3
- [x] Task: Verify Inheritance with Tests 443c4b3
- [ ] Task: Conductor - User Manual Verification 'Inheritance Logic (Backend)' (Protocol in workflow.md)

## Phase 2: UI Icon Update (Frontend)
Replacing the tree icon with the fork icon.

- [ ] Task: Update Icon in Sidebar
    - [ ] Locate the "tree" icon SVG in `app/templates/index.html` (or `script.js` if dynamically rendered) used for forked chat indicators.
    - [ ] Replace it with the new SVG fork path: `<path d="M5 5.372v.878c0 .414.336.75.75.75h4.5a.75.75 0 0 0 .75-.75v-.878a2.25 2.25 0 1 1 1.5 0v.878a2.25 2.25 0 0 1-2.25 2.25h-1.5v2.128a2.251 2.251 0 1 1-1.5 0V8.5h-1.5A2.25 2.25 0 0 1 3.5 6.25v-.878a2.25 2.25 0 1 1 1.5 0ZM5 3.25a.75.75 0 1 0-1.5 0 .75.75 0 0 0 1.5 0Zm6.75.75a.75.75 0 1 0 0-1.5.75.75 0 0 0 0 1.5Zm-3 8.75a.75.75 0 1 0-1.5 0 .75.75 0 0 0 1.5 0Z"></path>`
- [ ] Task: Update Fork Button Icon
    - [ ] Update the "Fork" button next to Gemini messages in `app/static/script.js` to use the new icon.
- [ ] Task: Conductor - User Manual Verification 'UI Icon Update (Frontend)' (Protocol in workflow.md)