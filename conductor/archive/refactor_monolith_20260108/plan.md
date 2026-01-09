# Plan: Refactor Monolithic Structure

## Phase 1: Preparation and Static Extraction [checkpoint: af6bda0]
- [x] Task: Create Project Structure 744eebc
    - [ ] Create directories: `app/`, `app/core`, `app/routers`, `app/models`, `app/services`, `app/templates`, `app/static`, `tests/`.
    - [ ] Create `app/__init__.py`.
- [x] Task: Extract Static Files c11a565
    - [ ] Move CSS content from `STATIC` dict in `py.py` to `app/static/style.css`.
    - [ ] Move JS content (if any embedded) to `app/static/`.
    - [ ] Verify static files are correctly placed.
- [x] Task: Extract Templates cdc020d
    - [ ] Move HTML content from `TEMPLATES` dict in `py.py` to individual files in `app/templates/` (e.g., `index.html`, `login.html`).
    - [ ] Verify template files are correctly placed.

## Phase 2: Core and Service modularization [checkpoint: f21d3b3]
- [x] Task: Extract Configuration 864b843
    - [ ] Create `app/core/config.py`.
    - [ ] Move constants like `SESSION_SECRET`, `RP_ID`, `ORIGIN` to `config.py`.
- [x] Task: Extract Services and Models d65a575
    - [ ] Move `UserDatabase` class to `app/services/user_manager.py` (or similar).
    - [ ] Move WebAuthn helper functions to `app/services/auth_service.py`.
    - [ ] Move Pydantic models (if any inline) to `app/models/`.

## Phase 3: Router Implementation and Entry Point [checkpoint: dee205e]
- [x] Task: Create Routers 529a92b
    - [ ] Create `app/routers/auth.py` and move login/registration endpoints there.
    - [ ] Create `app/routers/chat.py` and move chat-related endpoints there.
    - [ ] Create `app/routers/admin.py` and move admin endpoints there.
- [x] Task: Create Main Entry Point a45340c
    - [ ] Create `app/main.py`.
    - [ ] Initialize FastAPI app.
    - [ ] Configure StaticFiles mounting.
    - [ ] Configure TemplateResponse with new paths.
    - [ ] Include all routers.

## Phase 4: Validation and Cleanup [checkpoint: 0a11f29]
- [~] Task: Manual Verification
    - [ ] Run the app using `uvicorn app.main:app`.
    - [ ] Verify homepage loads.
    - [ ] Verify static assets load.
    - [ ] Verify login flow.
- [x] Task: Cleanup 9642aa8
    - [ ] Remove `py.py` (or rename to `py.py.bak` for safety initially).
    - [ ] Update `setup_py.sh` to point to the new entry point.
