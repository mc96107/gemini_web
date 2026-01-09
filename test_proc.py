import asyncio
import shutil
import os

async def test():
    cmd = shutil.which("gemini")
    print(f"Testing command: {cmd}")
    try:
        proc = await asyncio.create_subprocess_exec(cmd, "--version", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        stdout, stderr = await proc.communicate()
        print(f"Exec Status: {proc.returncode}")
        print(f"Stdout: {stdout.decode()}")
        print(f"Stderr: {stderr.decode()}")
    except Exception as e:
        print(f"Exec Failed: {e}")

    try:
        # For shell, we might need to quote the command if it has spaces
        proc = await asyncio.create_subprocess_shell(f'"{cmd}" --version', stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        stdout, stderr = await proc.communicate()
        print(f"Shell Status: {proc.returncode}")
        print(f"Stdout: {stdout.decode()}")
        print(f"Stderr: {stderr.decode()}")
    except Exception as e:
        print(f"Shell Failed: {e}")

asyncio.run(test())
