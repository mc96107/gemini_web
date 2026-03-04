---
name: recombine-and-deploy
description: Runs the build and deployment pipeline for the opencode_agent_release.py file
---

# Recombine and Deploy Pipeline

Use this skill when you need to deploy changes made to the codebase. It builds the single-file release, copies it to the production directory, restarts the service, and commits/pushes the changes to the repository.

## Workflow

1. **Verify working directory:** Ensure you are in `/home/z/o/ocdev`.
2. **Build the release:** Run the recombination script:
   ```bash
   python scripts/recombine.py
   ```
3. **Deploy to production:** Copy the generated file to the parent directory:
   ```bash
   cp opencode_agent_release.py /home/z/o/
   ```
4. **Restart the service:** Restart the systemd user service:
   ```bash
   systemctl --user restart oc
   ```
5. **Verify service status:** Ensure the service started successfully:
   ```bash
   systemctl --user status oc --no-pager
   ```
6. **Commit and push:**
   - Run `git status` and `git diff` to review changes
   - Create a descriptive commit message summarizing the changes
   - Commit all tracked changes (`git commit -am "..."` or add specific files)
   - Push to the remote repository

## Important Notes

- Always check the service status after restarting to ensure the deployment was successful.
- If `recombine.py` fails (e.g. due to syntax errors in the source files), do NOT proceed with deployment or committing.
- Ensure the commit message accurately reflects the changes being deployed.
