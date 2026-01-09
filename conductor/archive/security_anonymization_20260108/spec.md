# Specification: Application Hardening & Anonymization

## 1. Overview
Remove all hardcoded personal identifiers, secrets, and environment-specific URLs to prepare the application for public use.

## 2. Goals
*   Make `RP_ID` and `ORIGIN` configurable via environment.
*   Implement a first-run setup for the admin password.
*   Anonymize all remaining personal data.
*   Harden session and security headers.

## 3. Key Features
*   `.env` support for configuration.
*   First-run setup wizard.
*   Security middleware integration.
