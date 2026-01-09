# Specification: Refactor Monolithic Structure

## 1. Overview
The current application resides in a single file `py.py`. This track aims to decompose this monolith into a modular structure following standard FastAPI project layouts. This will enhance code readability, maintainability, and testability.

## 2. Goals
*   Separate concerns by moving logic into dedicated modules (e.g., routing, authentication, models, utilities).
*   Extract HTML templates and static assets (CSS, JS) into their respective directories.
*   Ensure the application functionality remains identical after refactoring ("Green-Green" refactoring).
*   Establish a foundation for future feature development.

## 3. Proposed Structure
The project should be reorganized into the following structure:
```
gemini_web/
├── app/
│   ├── __init__.py
│   ├── main.py          # Entry point, app initialization
│   ├── core/            # Config, security, database setup
│   │   ├── config.py
│   │   ├── security.py
│   ├── routers/         # API routes
│   │   ├── auth.py
│   │   ├── chat.py
│   │   ├── admin.py
│   ├── models/          # Pydantic models & DB schemas
│   │   ├── user.py
│   ├── services/        # Business logic (e.g., WebAuthn, Ethereum)
│   │   ├── auth_service.py
│   │   ├── llm_service.py
│   ├── templates/       # Jinja2 templates (moved from py.py)
│   └── static/          # CSS, JS, Images (moved from py.py)
├── tests/               # Tests
├── requirements.txt
└── README.md
```

## 4. Key Refactoring Steps
1.  **Extract Static Assets:** Move CSS and JS content from Python dictionaries in `py.py` to `.css` and `.js` files in `app/static/`.
2.  **Extract Templates:** Move HTML content from Python dictionaries in `py.py` to `.html` files in `app/templates/`.
3.  **Modularize Code:**
    *   Create `app/core/config.py` for settings (e.g., `SESSION_SECRET`, `RP_ID`).
    *   Create `app/models/` for any data structures.
    *   Create `app/services/` for logic like `UserDatabase`, `WebAuthn` helpers.
    *   Create `app/routers/` to split the endpoints defined in `py.py`.
4.  **Update Entry Point:** Create `app/main.py` to assemble the FastAPI app and include routers.

## 5. Validation
*   The application must start successfully using `uvicorn app.main:app --reload`.
*   All existing features (Login, Chat, Admin) must function exactly as before.
*   No new features are to be added in this track.
