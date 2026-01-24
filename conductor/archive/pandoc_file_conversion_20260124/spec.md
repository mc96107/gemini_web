# Specification: Pandoc File Conversion

## Overview
This feature automatically converts uploaded `.docx` and `.xlsx` files into Markdown (`.md`) format using Pandoc. The goal is to provide the AI model with readable text content from structured documents while minimizing tokens by excluding images.

## Functional Requirements
- **Automatic Conversion:** When a user uploads a `.docx` or `.xlsx` file, the system detects the extension and triggers a Pandoc conversion.
- **Markdown Output:** The result of the conversion must be a Markdown file.
- **Exclude Images:** The conversion process must explicitly exclude or strip any images contained within the original documents.
- **Fallback Mechanism:** If conversion fails, the system should log the error and either proceed with the original file (if supported by Gemini) or notify the user.
- **Integration:** The converted `.md` file should be used as the attachment for the chat message instead of the original binary file.

## Tech Stack Considerations
- **Pandoc:** Requires `pandoc` to be installed on the host system (Termux/Windows).
- **Python Library:** Use a wrapper like `pypandoc` or execute the CLI directly via `asyncio.create_subprocess_exec`.

## Acceptance Criteria
- [ ] Uploading a `.docx` file results in a `.md` version being processed by the agent.
- [ ] Uploading a `.xlsx` file results in a `.md` (likely table format) version being processed.
- [ ] The converted Markdown files do not contain embedded images or references to externalized images from the doc.
- [ ] The user receives a seamless experience where they upload the doc and the AI "reads" its content.
