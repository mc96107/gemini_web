# Implementation Plan: Gemini CLI v0.28+ Updates

## Phase 1: Tool Renaming & Model Updates
- [x] Rename `search_file_content` to `grep_search` in `app/templates/index.html`. 206fe5f
- [x] Update `FALLBACK_MODELS` and model constants in `app/services/llm_service.py`. 206fe5f
- [x] Update model selection list in `app/templates/index.html`. 7932628

## Phase 2: Plan Mode Integration
- [ ] Update `app/routers/chat.py` to recognize `/plan` command.
- [ ] Modify `GeminiAgent.generate_response_stream` to pass `--plan` flag when appropriate.
- [ ] Add UI indicators/modals for Plan Mode execution and review.

## Phase 3: Admin & MCP Support
- [ ] Add MCP configuration section to `app/templates/admin.html`.
- [ ] Implement backend routes in `app/routers/admin.py` for MCP management.
- [ ] Update `config.py` to handle MCP-related settings.

## Phase 4: Agent Skills Support
- [ ] Add skill management UI to Agent Editor.
- [ ] Ensure skills in `.agents/skills` are correctly discovered and linked.
