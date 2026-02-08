# Technology Stack - Gemini Termux Agent

## Backend
* **Language:** Python 3
* **State Management:** Pydantic models for tracking complex session state (e.g., prompt building trees).
* **Configuration:** Persistent global settings stored in `data/settings.json` for runtime application customization.
* **Orchestration Metadata:** Wiki-link style YAML frontmatter (`[[path/to/agent.md]]`) for hierarchical agent linking and tracking.
* **Framework:** FastAPI - A modern, fast (high-performance) web framework for building APIs with Python 3.7+ based on standard Python type hints.
* **Streaming:** Server-Sent Events (SSE) via FastAPI `StreamingResponse`.
* **Server:** Uvicorn - An ASGI web server implementation for Python.

## Frontend
* **Templating:** Jinja2 - A modern and designer-friendly templating language for Python.
* **Styling:** Bootstrap 5 - A powerful, extensible, and feature-packed frontend toolkit.
* **Image Processing:** Browser Canvas API - For high-performance, client-side image compression and resizing.
* **Math Rendering:** KaTeX - Fast, lightweight LaTeX math rendering library.
* **Voice Interaction:** Web Speech API (SpeechRecognition & SpeechSynthesis) - For hands-free conversation loops.
* **Power Management:** Screen Wake Lock API - To keep the device active during voice-only sessions.
* **Icons:** Bootstrap Icons - A free, high-quality, open-source icon library.

## Security & Authentication
* **Passkeys:** WebAuthn / `webauthn` library - For implementing passwordless, FIDO2-compliant authentication.
* **Blockchain Identity:** `eth-account` - For Ethereum-based cryptographic signing and authentication.
* **Hashing:** `bcrypt` - For secure password hashing (where applicable).
* **Session Management:** `itsdangerous` & Starlette SessionMiddleware - For secure session handling.
* **File Security:** `pathlib.Path.name` - Used for robust filename sanitization to prevent path traversal vulnerabilities in file retrieval routes.

## Document Processing

*   **Pandoc:** A universal document converter used to transform `.docx` and `.xlsx` files into Markdown for AI consumption.

*   **pypandoc:** Python wrapper for Pandoc CLI.

*   **Ghostscript:** Used for high-performance PDF optimization and compression.

*   **Pandas:** Used for robust extraction and conversion of `.xlsx` spreadsheets to Markdown tables.
* **Tabulate:** Dependency for Pandas to generate well-formatted Markdown tables.

## Runtime & Deployment
* **Environment:** Android Termux - A terminal emulator and Linux environment for Android.
* **Service Management:** `termux-services` (runit) - For managing background services and ensuring the agent remains running.
