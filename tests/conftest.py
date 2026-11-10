"""Pytest configuration and test mocks."""
from __future__ import annotations

import asyncio
import inspect
import sys
from unittest.mock import MagicMock

# Pure-python synchronous coroutine runner for sandboxed Windows environments
# Avoids Windows Proactor/IOCP anonymous pipe deadlocks when running inside sandboxes
def _sandboxed_async_run(coro):
    stack = [coro.__await__() if hasattr(coro, "__await__") else coro]
    res = None
    while stack:
        curr = stack[-1]
        try:
            val = curr.send(res)
            res = None
            if hasattr(val, "__await__"):
                stack.append(val.__await__())
        except StopIteration as exc:
            stack.pop()
            res = exc.value
    return res

asyncio.run = _sandboxed_async_run

# Mock asyncpg if not installed locally so models & schemas can be tested offline
if "asyncpg" not in sys.modules:
    try:
        import asyncpg
    except ImportError:
        mock_asyncpg = MagicMock()
        mock_asyncpg.exceptions = MagicMock()
        sys.modules["asyncpg"] = mock_asyncpg
        sys.modules["asyncpg.exceptions"] = mock_asyncpg.exceptions
