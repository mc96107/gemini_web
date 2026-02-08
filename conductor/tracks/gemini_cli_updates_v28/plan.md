# Implementation Plan: Gemini CLI v0.28+ Updates

## Phase 1: Tool Renaming & Model Updates [checkpoint: cfa8e49]
- [x] Rename `search_file_content` to `grep_search` in `app/templates/index.html`. 206fe5f
- [x] Update `FALLBACK_MODELS` and model constants in `app/services/llm_service.py`. 206fe5f
- [x] Update model selection list in `app/templates/index.html`. 7932628

## Phase 2: Plan Mode Integration [checkpoint: 2dbafbd]
- [x] Update `app/routers/chat.py` to recognize `/plan` command. 9b076d6
- [x] Modify `GeminiAgent.generate_response_stream` to pass `--plan` flag when appropriate. 9b076d6
- [x] Add UI indicators/modals for Plan Mode execution and review. ddb3c10

## Phase 3: Admin & MCP Support
- [x] Add MCP configuration section to `app/templates/admin.html`. 394369e
- [x] Implement backend routes in `app/routers/admin.py` for MCP management. 394369e
- [ ] Update `config.py` to handle MCP-related settings.

## Phase 4: Agent Skills Support
- [ ] Add skill management UI to Agent Editor.
- [ ] Ensure skills in `.agents/skills` are correctly discovered and linked.
