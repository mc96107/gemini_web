# Specification: Line Ending Normalization

## 1. Overview
Resolve the recurring Git warning: "LF will be replaced by CRLF the next time Git touches it" by enforcing consistent line endings across the repository.

## 2. Goals
*   Eliminate platform-dependent line ending discrepancies.
*   Ensure all code files are normalized to LF in the repository.

## 3. Implementation
*   Create a `.gitattributes` file.
*   Normalize existing files.
