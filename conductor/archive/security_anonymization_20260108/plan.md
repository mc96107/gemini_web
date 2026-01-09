# Plan: Application Hardening & Anonymization

## Phase 1: Configuration & Anonymization
- [x] Task: Implement .env Configuration 22cafbe
    - [ ] Use `python-dotenv` to load settings in `app/core/config.py`.
    - [ ] Create `.env.example`.
- [x] Task: Remove Hardcoded Identity 22cafbe
    - [ ] Replace `your-domain.com` with environment variables.
    - [ ] Remove hardcoded `SESSION_SECRET`.
- [x] Task: Anonymize Codebase 9fb29f8
    - [ ] Scrub all personal usernames, IP addresses, or keys from the source code.

## Phase 2: Setup & Hardening [checkpoint: 6d8035e]
- [x] Task: Implement First-Run Setup 359b192
    - [ ] Add logic to prompt for admin password if `users.json` is missing.
- [x] Task: Security Hardening 63d5f9c
    - [ ] Add HSTS, CSP, and X-Content-Type-Options headers.
    - [ ] Secure session cookies.
- [x] Task: Verification
    - [ ] Verify clean startup and configuration loading.
