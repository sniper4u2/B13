"""
B13 Agent Tool Layer - Base Classes

All tools inherit from smolagents.Tool directly.
Backends are lazily initialized on first forward() call.

IMPORTANT (smolagents contract): smolagents calls `Tool.forward()` SYNCHRONOUSLY
and uses its return value directly. B13 backends are async, so `forward()` here
is a SYNC method that drives the async backend through an event loop. Do NOT make
forward async again - an async forward returns an un-awaited coroutine and the
tool silently never executes.
"""

import asyncio
import logging
from typing import Any

from smolagents import Tool

logger = logging.getLogger(__name__)


def run_async(coro):
    """Run an awaitable to completion from sync code (smolagents tool call).

    Handles both "no running loop" and "already inside a loop" cases.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop is not None and loop.is_running():
        # Already inside a loop: run in a fresh loop on a private thread.
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
            return ex.submit(lambda: asyncio.run(coro)).result()
    return asyncio.run(coro)


class B13Tool(Tool):
    """
    Base class for B13 agent tools.

    Backend connections are lazy - only initialized when forward() is called.
    This makes tools importable and instantiable on Kaggle without backends.
    """
    name: str
    description: str
    inputs: dict[str, dict[str, str | type | bool]]
    output_type: str
    output_schema: dict[str, Any] | None = None

    def __init__(self, *args, **kwargs):
        self.is_initialized = False
        super().__init__(*args, **kwargs)
        self._backend = None

    def _get_backend(self):
        """Override to return the backend instance. Called lazily."""
        return None

    def forward(self, *args, **kwargs) -> dict:
        """SYNC entry point (smolagents calls this synchronously).

        Initializes the backend lazily and drives the async backend call to
        completion so the tool actually executes and returns its real result.
        """
        if self._backend is None:
            self._backend = self._get_backend()

        if self._backend is None:
            raise RuntimeError(
                f"Tool '{self.name}' backend is not available. "
                f"This tool requires a local environment with the necessary dependencies."
            )

        return run_async(self._backend_call(*args, **kwargs))

    async def _backend_call(self, *args, **kwargs) -> dict:
        """Override to call the specific backend method."""
        raise NotImplementedError("Subclasses must implement _backend_call")
