# Specification - Safely Handle Extremely Large Tool Outputs

## Problem
When tools (like file reading or complex calculations) return very large amounts of data, it can cause issues:
- Browser performance degradation.
- Token limit exhaustion for the LLM.
- WebSocket message size limits.
- UI clutter.

## Proposed Solution
- Implement a truncation mechanism for tool outputs before they are sent to the LLM and the frontend.
- Provide a way for the user (and the LLM) to know that output was truncated.
- Optionally allow the user to see the full output via a dedicated viewer or file download.

## Requirements
- Backend: Detect tool output size.
- Logic: If output > threshold (e.g., 20KB), truncate and add a message like `[Output truncated. Full output available in ...]`.
- LLM: The LLM should be informed that it is seeing a truncated version of the output.
- Storage: Store large outputs as files or in a temporary storage if the user needs to see the full content.
