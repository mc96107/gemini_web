# Specification - Persist Model Switch on Quota Exhaustion

## Problem
When a model (e.g., Pro) hits a quota limit (429), the backend correctly switches to a fallback model (e.g., Flash) for the current response. However:
- The UI model selection button doesn't permanently reflect this change.
- Subsequent messages in the same session still attempt to use the exhausted model, leading to repeated failures and fallback delays.

## Proposed Solution
- Update the frontend state (`modelInput.value`) when a `model_switch` event is received.
- Update the UI (active state in the model menu and the footer label) to show the new model.
- This ensures that the next request sent by the user will use the fallback model directly.

## Requirements
- Frontend: `script.js` must handle `model_switch` event by:
    - Setting `modelInput.value` to `data.new_model`.
    - Updating `.active` class on model links.
    - Updating `#model-label` text.
