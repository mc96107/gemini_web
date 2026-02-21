# Specification: Gemini CLI v0.28+ Updates

## Overview
Update the Gemini Web project to align with the latest features and changes introduced in `gemini-cli` version 0.28.0 and above.

## Scope
1. **Tool Renaming:** Update `search_file_content` to `grep_search` across UI and backend.
2. **Plan Mode Integration:** Implement support for the new `/plan` command and plan-specific tools.
3. **MCP Support:** Add admin-level configuration for MCP servers.
4. **Agent Skills:** Integrate support for the `.agents/skills` lifecycle.
5. **Model List Update:** Ensure latest Gemini 3 models are correctly listed and prioritized.

## Requirements
- Maintain backward compatibility where possible.
- Update UI components (modals, buttons) to reflect new capabilities.
- Update `llm_service.py` and `chat.py` to handle new commands and tool names.
