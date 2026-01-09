# Specification: Release Bundling Tooling

## 1. Overview
Implement a script that can recombine the modularized `app/` structure (templates, static assets, and logic) back into a single-file release if needed, or package it for distribution.

## 2. Goals
*   Automate the creation of a "production" bundle.
*   Provide a way to generate a single-file version of the application for simple deployment (like the original `py.py`).

## 3. Implementation
*   A Python script that reads the modular structure and synthesizes a target release file.
