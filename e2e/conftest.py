"""e2e conftest — import sandboxed runner."""
from tests.conftest import _sandboxed_async_run
import asyncio
asyncio.run = _sandboxed_async_run

