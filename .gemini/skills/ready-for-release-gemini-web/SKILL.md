---
name: ready-for-release-gemini-web
description: Executes the deployment and release workflow for Gemini Web. Automatically increments the version number based on the latest git tag. Use this when the project is ready for a new production release.
---

# Ready For Release Gemini Web

This skill automates the sequential process of deploying the consolidated release bundle to the production server and finalizing the release on Git/GitHub. It automatically determines the next version number by incrementing the patch version of the latest git tag.

## Workflow

### 1. Deploy Consolidated Bundle
Execute the secure copy of the release artifact to the target production server.

```bash
scp gemini_agent_release.py z@192.168.1.84:g
scp gemini_agent_release.py z@192.168.1.84:gg/law
scp gemini_agent_release.py z@192.168.1.84:gg/school
```

### 2. Restart Server
Execute the server restart command via SSH.

```bash
ssh z@192.168.1.84 "sudo systemctl restart gemini-agent"
ssh z@192.168.1.84 "sudo systemctl restart gemini-agent-law"
ssh z@192.168.1.84 "sudo systemctl restart gemini-agent-school"
```

### 3. Determine Next Version
The skill will automatically calculate the next version. You can also run this command to see it:

```powershell
$current = git describe --tags --abbrev=0; $parts = $current.TrimStart('v').Split('.'); $nextVersion = "$($parts[0]).$($parts[1]).$([int]$parts[2] + 1)"; echo "Next version: $nextVersion"
```

### 4. Finalize Git Changes
Stage all changes, commit with the new version number, and push.

```powershell
# Automated sequence
$current = git describe --tags --abbrev=0; $parts = $current.TrimStart('v').Split('.'); $nextVersion = "$($parts[0]).$($parts[1]).$([int]$parts[2] + 1)";
git add .;
git commit -m "chore: release version $nextVersion";
git push;
```

### 5. Create GitHub Release
Create a new formal release on GitHub using the calculated version.
Include release docs and gemini_agent_release.py

```powershell
# Continued from previous step
gh release create "v$nextVersion" --generate-notes
```

## Usage Guidelines

- Ensure `gemini_agent_release.py` has been generated and verified before triggering this workflow.
- This skill assumes a `vMAJOR.MINOR.PATCH` tagging format.
- The `scp` command targets user `z` at IP `192.168.1.84`.
