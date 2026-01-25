import asyncio
import sys

# Force ProactorEventLoop on Windows for subprocess support
# This must be done as early as possible.
if sys.platform == 'win32':
    try:
        from asyncio import WindowsProactorEventLoopPolicy
        asyncio.set_event_loop_policy(WindowsProactorEventLoopPolicy())
    except ImportError:
        pass
