# OpenCode Database Schema Notes

This document tracks the OpenCode SQLite database schema used by the application. If the schema changes, the files listed below will need updating.

**Database Location:** `/home/z/.local/share/opencode/opencode.db`

---

## Current Schema (as of 2026-03-02, VERIFIED)

### Tables

#### `session`
| Column | Type | Description |
|--------|------|-------------|
| id | TEXT | Session UUID |
| project_id | TEXT | Foreign key to project |
| parent_id | TEXT | Parent session (for forks) |
| slug | TEXT | URL-safe identifier |
| directory | TEXT | Session working directory |
| title | TEXT | Session title |
| version | TEXT | Schema version |
| share_url | TEXT | Shared URL if published |
| summary_additions | INTEGER | Git diff additions |
| summary_deletions | INTEGER | Git diff deletions |
| summary_files | INTEGER | Files changed count |
| summary_diffs | TEXT | Diff details |
| revert | TEXT | Revert info |
| permission | TEXT | Permission level |
| time_created | INTEGER | Unix timestamp |
| time_updated | INTEGER | Unix timestamp |
| time_compacting | INTEGER | Compaction timestamp |
| time_archived | INTEGER | Archive timestamp |

#### `message`
| Column | Type | Description |
|--------|------|-------------|
| id | TEXT | Message UUID |
| session_id | TEXT | Foreign key to `session.id` |
| time_created | INTEGER | Unix timestamp |
| time_updated | INTEGER | Unix timestamp |
| data | TEXT | JSON blob containing message METADATA (not content!) |

#### `message.data` JSON Structure (METADATA ONLY)
```json
{
  "role": "user" | "assistant",
  "time": { "created": 1234567890, "completed": 1234567890 },
  "parentID": "msg_...",
  "modelID": "model-name",
  "providerID": "provider-name",
  "mode": "build" | "plan",
  "path": { "cwd": "...", "root": "..." },
  "cost": 0,
  "tokens": { "input": 0, "output": 0, "reasoning": 0, "cache": { "read": 0, "write": 0 } }
}
```
NOTE: `role` is at TOP LEVEL (NOT nested under `info`). User messages may also have `summary` instead of model fields.

#### `part` (NEW - message content lives here)
| Column | Type | Description |
|--------|------|-------------|
| id | TEXT | Part UUID |
| message_id | TEXT | Foreign key to `message.id` |
| session_id | TEXT | Foreign key to `session.id` |
| time_created | INTEGER | Unix timestamp |
| time_updated | INTEGER | Unix timestamp |
| data | TEXT | JSON blob containing part content |

#### `part.data` JSON Structure (varies by type)
```json
// type: "text" - actual message text
{ "type": "text", "text": "message content here", "synthetic": true|false }

// type: "reasoning" - AI thinking/reasoning
{ "type": "reasoning", "text": "thinking content", "time": { "start": ..., "end": ... } }

// type: "tool" - tool call and result
{ "type": "tool", "callID": "call_...", "tool": "bash|read|write|...",
  "state": { "status": "completed", "input": {...}, "output": "...", "title": "..." } }

// type: "step-start" - marks beginning of a step
{ "type": "step-start" }

// type: "step-finish" - marks end of a step with cost
{ "type": "step-finish", "reason": "tool-calls|end-turn", "cost": 0, "tokens": {...} }

// type: "file" - file reference
{ "type": "file", ... }
```

---

## CRITICAL: Schema Change History

**2026-03-02**: Schema broke our SQLite reader because:
- OLD assumption: `message.data` contained `{ info: {role}, parts: [{type, text}] }` (all-in-one)
- NEW reality: `message.data` only has metadata; content is in separate `part` table
- Fix: `read_session_from_sqlite()` now JOINs message + part tables and reconstructs the old format

---

## Files That Use This Schema

If the schema changes, edit these files:

1. **`app/services/llm_service.py`**
   - Function: `read_session_from_sqlite()`
   - Function: `get_session_messages()`

2. **`opencode_agent_release.py`** (auto-generated via `scripts/recombine.py`)

---

## Fallback Mechanism

The code uses `opencode export` as a fallback if direct SQLite reading fails:
- Primary: Direct SQLite query (faster)
- Fallback: `opencode export <session_uuid>` (slower but guaranteed compatible)

---

## Updating This Document

When OpenCode updates its schema:
1. Query the database: `SELECT name FROM sqlite_master WHERE type='table';`
2. Get columns: `PRAGMA table_info(<table>);`
3. Sample data: `SELECT data FROM <table> LIMIT 3;`
4. Update this doc and `read_session_from_sqlite()`
5. Run `scripts/recombine.py` to rebuild release
