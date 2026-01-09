# Plan: Fabric Patterns Expansion & Sync

Expand the list of patterns and add a way to sync them from the official repository.

## Tasks
- [x] Refactor `app/core/patterns.py` to load patterns from a JSON/YAML file.
- [x] Implement a service to fetch patterns from `https://github.com/danielmiessler/Fabric/tree/main/data/patterns`.
- [x] Sanitize patterns to remove Fabric-specific CLI instructions.
- [x] Add an admin web interface to trigger pattern updates.
- [x] Verify that new patterns are available in the chat interface.
