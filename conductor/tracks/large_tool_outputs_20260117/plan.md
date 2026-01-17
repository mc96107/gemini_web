# Implementation Plan - Safely Handle Extremely Large Tool Outputs

## User Review Required

> [!IMPORTANT]
> We need to define the "safe" threshold for tool outputs. 20-30KB is usually a safe limit for real-time interaction, but we should verify the token cost for the models we use.

## Proposed Changes

### Backend
- [x] In `app/services/llm_service.py` (or where tool results are processed), add a size check. 0c81b5d
- [x] Implement a `truncate_tool_output` utility function. 0c81b5d
- [x] Update the tool execution loop to use this utility. 0c81b5d

### Frontend
- [x] Handle the display of truncated messages in `app/static/script.js`. c88197d
- [x] (Optional) Add a "Show more" or "Download full output" link for truncated content. c88197d

## Verification Plan

### Automated Tests
- [x] Create a mock tool that returns a 1MB string. 0c81b5d
- [x] Verify that the backend truncates it before sending it to the LLM. 0c81b5d
- [x] Verify that the truncated output contains the "truncated" warning. 0c81b5d

### Manual Verification
- [ ] Trigger a tool that produces large output (e.g., read a large file if such a tool exists).
- [ ] Verify that the UI remains responsive and the output is readable.
