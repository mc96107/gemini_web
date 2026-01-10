import asyncio
import shutil
import os

async def test():
    gemini_cmd = shutil.which("gemini") or "gemini"
    
    # Case 1: Allow ONLY read_file. Try run_shell_command.
    # According to docs, allowed-tools is comma-separated.
    print("Testing allow read_file only...")
    proc = await asyncio.create_subprocess_exec(
        gemini_cmd,
        "Run shell command 'echo hello'",
        "--approval-mode", "default",
        "--allowed-tools", "read_file",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()
    print("STDOUT:", stdout.decode())
    print("STDERR:", stderr.decode())

    # Case 2: Allow run_shell_command. Should run.
    print("\nTesting allow run_shell_command...")
    proc = await asyncio.create_subprocess_exec(
        gemini_cmd,
        "Run shell command 'echo hello'",
        "--approval-mode", "default",
        "--allowed-tools", "run_shell_command",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()
    print("STDOUT:", stdout.decode())
    print("STDERR:", stderr.decode())

    # Case 3: Multiple tools.
    print("\nTesting multiple allowed tools (read_file,run_shell_command)...")
    proc = await asyncio.create_subprocess_exec(
        gemini_cmd,
        "Run shell command 'echo hello'",
        "--approval-mode", "default",
        "--allowed-tools", "read_file,run_shell_command",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()
    print("STDOUT:", stdout.decode())
    print("STDERR:", stderr.decode())

if __name__ == "__main__":
    asyncio.run(test())