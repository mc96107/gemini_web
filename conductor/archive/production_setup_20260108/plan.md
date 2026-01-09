# Plan: Production Configuration

Support custom base URL and production readiness.

## Tasks
- [x] Add `BASE_URL` (or `ORIGIN`) configuration to the setup process.
- [x] Update `app/templates/setup.html` to include a field for the custom URL.
- [x] Update `app/core/config.py` to handle the new configuration.
- [x] Verify that the application correctly uses the configured base URL for links and redirects.
