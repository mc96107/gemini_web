---
name: ready-for-release-gemini-web
description: Executes the deployment and release workflow for Gemini Web. Use this when the project is ready for a new production release to remote servers and GitHub.
---

# Ready For Release Gemini Web

This skill automates the sequential process of deploying the consolidated release bundle to the production server and finalizing the release on Git/GitHub.

## Workflow

### 1. Deploy Consolidated Bundle
Execute the secure copy of the release artifact to the target production server.

```bash
scp gemini_agent_release.py z@192.168.1.84:g
```

### 2. Finalize Git Changes
Stage all changes (including the updated release artifact), commit with a descriptive release message, and push to the remote repository.

```bash
git add .
git commit -m "chore: release version [version_number]"
git push
```

### 3. Create GitHub Release
Create a new formal release on GitHub using the GitHub CLI.

```bash
# Example: Create a release with automatically generated notes
gh release create v[version_number] --generate-notes
```

## Usage Guidelines

- Ensure `gemini_agent_release.py` has been generated and verified before triggering this workflow.
- Always confirm the `[version_number]` with the user before performing the Git commit and GitHub release steps.
- The `scp` command targets user `z` at IP `192.168.1.84`.
