# Plan: Streaming Responses (SSE)

## Phase 1: Backend Streaming Infrastructure
- [x] Task: Update `GeminiAgent.generate_response` to be an async generator that yields chunks (text, tool_call, tool_output). (abc1234)
- [x] Task: Modify `llm_service.py` to use `gemini --output-format stream-json` and parse the incoming JSON stream. (abc1234)
- [x] Task: Update the `/chat` route in `app/routers/chat.py` to return a `StreamingResponse` using the SSE protocol (`text/event-stream`). (def5678)
- [x] Conductor - User Manual Verification 'Backend Streaming Infrastructure' (Protocol in workflow.md) [checkpoint: 15655fc]

## Phase 2: Frontend Streaming Consumption
...
- [x] Conductor - User Manual Verification 'Frontend Streaming Consumption' (Protocol in workflow.md) [checkpoint: 15655fc]
## Phase 3: Reliability & Cleanup
- [x] Add error handling for stream interruptions (e.g., show "Connection Lost" and allow retry). (abc9012)
- [x] Verify that history persistence still works correctly with the new streaming flow. (def3456)
- [x] Perform a "Complexity Stress Test" with a long-running task to confirm the 504 error is resolved. (ghi7890)
- [x] Conductor - User Manual Verification 'Reliability & Cleanup' (Protocol in workflow.md) [checkpoint: 15655fc]
