# Specification: Math Rendering

## Overview
Enable rendering of mathematical expressions in chat messages using KaTeX. This ensures that formulas formatted in LaTeX syntax (e.g., $E=mc^2$) are displayed correctly, matching the experience in tools like Obsidian.

## Functional Requirements
- **Library Integration:** Include KaTeX CSS and JS libraries via CDN in the application.
- **Auto-Rendering:** Automatically render math expressions within chat message bubbles upon display.
- **Syntax Support:** Support both inline (`$...$`) and block (`$$...$$`) math delimiters.

## Acceptance Criteria
- [ ] Chat messages containing `$x^2$` render as formatted math.
- [ ] Chat messages containing `$$ \sum $$` render as block math.
- [ ] No significant performance regression during message rendering.
