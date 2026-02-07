# Specification: Fix Conversation Branching Point

**Overview**
Correct the issue where forking a conversation from a specific message in the main chat interface results in a new session starting from an incorrect point, typically missing the user-selected message.

**Functional Requirements**
1.  **Accurate Message Indexing:** Ensure that every message rendered in the chat interface correctly tracks its absolute index within the raw session data, regardless of whether any messages are filtered or skipped during rendering.
2.  **Precise Truncation:** Update the forking logic to use the verified raw message index to truncate the conversation history accurately, ensuring the selected message and all preceding history are preserved in the new session.
3.  **Tool Call Compatibility:** The forking mechanism must handle conversations containing tool call logs correctly, maintaining the relationship between user messages and their respective bot responses/tool outputs even when certain elements are hidden from the primary chat view.

**Acceptance Criteria**
-   [ ] Clicking "Fork" on any message (user or bot) creates a new session that includes that specific message and all history before it.
-   [ ] Forking a conversation with "occasional" tool calls correctly preserves the history up to the fork point without skipping the selected message.
-   [ ] The UI correctly switches to and loads the newly created session with the expected truncated history.

**Out of Scope**
-   Implementing a visual tree editor for branching (this fix focus on the existing "Fork" button logic).
-   Changing the storage format of session files.