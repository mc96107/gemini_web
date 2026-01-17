# Implementation Plan - Safely Handle Extremely Large Tool Outputs

## User Review Required

> [!IMPORTANT]
> We need to define the "safe" threshold for tool outputs. 20-30KB is usually a safe limit for real-time interaction, but we should verify the token cost for the models we use.

## Proposed Changes

### Backend
- [ ] In `app/services/llm_service.py` (or where tool results are processed), add a size check.
- [ ] Implement a `truncate_tool_output` utility function.
- [ ] Update the tool execution loop to use this utility.

### Frontend
- [ ] Handle the display of truncated messages in `app/static/script.js`.
- [ ] (Optional) Add a "Show more" or "Download full output" link for truncated content.

## Verification Plan

### Automated Tests
- [ ] Create a mock tool that returns a 1MB string.
- [ ] Verify that the backend truncates it before sending it to the LLM.
- [ ] Verify that the truncated output contains the "truncated" warning.

### Manual Verification
- [ ] Trigger a tool that produces large output (e.g., read a large file if such a tool exists).
- [ ] Verify that the UI remains responsive and the output is readable.
