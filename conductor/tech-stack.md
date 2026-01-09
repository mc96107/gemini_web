# Technology Stack - Gemini Termux Agent

## Backend
* **Language:** Python 3
* **Framework:** FastAPI - A modern, fast (high-performance) web framework for building APIs with Python 3.7+ based on standard Python type hints.
* **Server:** Uvicorn - An ASGI web server implementation for Python.

## Frontend
* **Templating:** Jinja2 - A modern and designer-friendly templating language for Python.
* **Styling:** Bootstrap 5 - A powerful, extensible, and feature-packed frontend toolkit.
* **Icons:** Bootstrap Icons - A free, high-quality, open-source icon library.

## Security & Authentication
* **Passkeys:** WebAuthn / `webauthn` library - For implementing passwordless, FIDO2-compliant authentication.
* **Blockchain Identity:** `eth-account` - For Ethereum-based cryptographic signing and authentication.
* **Hashing:** `bcrypt` - For secure password hashing (where applicable).
* **Session Management:** `itsdangerous` & Starlette SessionMiddleware - For secure session handling.

## Runtime & Deployment
* **Environment:** Android Termux - A terminal emulator and Linux environment for Android.
* **Service Management:** `termux-services` (runit) - For managing background services and ensuring the agent remains running.
