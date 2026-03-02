# OpenCode Database Schema Notes

This document tracks the OpenCode SQLite database schema used by the application. If the schema changes, the files listed below will need updating.

**Database Location:** `/home/z/.local/share/opencode/opencode.db`

---

## Current Schema (as of 2026-03-02)

### Tables

#### `session`
| Column | Type | Description |
|--------|------|-------------|
| id | TEXT | Session UUID |
| title | TEXT | Session title |
| time_created | INTEGER | Unix timestamp |
| time_updated | INTEGER | Unix timestamp (most recent activity) |
| directory | TEXT | Session working directory |
| slug | TEXT | URL-safe identifier |

#### `message`
| Column | Type | Description |
|--------|------|-------------|
| id | TEXT | Message UUID |
| session_id | TEXT | Foreign key to `session.id` |
| time_created | INTEGER | Unix timestamp |
| time_updated | INTEGER | Unix timestamp |
| data | TEXT | JSON blob containing message content |

#### `message.data` JSON Structure
```json
{
  "info": {
    "role": "user" | "assistant",
    "model": "model name (optional)"
  },
  "parts": [
    {
      "type": "text",
      "text": "message content here"
    },
    {
      "type": "reasoning", 
      "text": "AI reasoning/thinking (optional)"
    }
  ]
}
```

---

## Files That Use This Schema

If the schema changes, edit these files:

1. **`app/services/llm_service.py`**
   - Function: `read_session_from_sqlite()`
   - Function: `get_session_messages()`
   - Lines ~1723-1900 (get_session_messages with fallback logic)

2. **`opencode_agent_release.py`** (auto-generated via recombine.py)
   - Contains the combined/rebuilt version of llm_service.py

---

## Fallback Mechanism

The code uses `opencode export` as a fallback if direct SQLite reading fails:
- Primary: Direct SQLite query (faster)
- Fallback: `opencode export <session_uuid>` (slower but guaranteed compatible)

To disable direct SQLite and always use export, set environment variable or add a flag (not currently implemented - would need code change).

---

## Updating This Document

When OpenCode updates its schema:
1. Query the database to get current schema: `PRAGMA table_info(message);`
2. Update the tables above with new/removed columns
3. Update the `message.data` JSON structure if it changes
4. Update the affected functions in `app/services/llm_service.py`
5. Document any breaking changes here
