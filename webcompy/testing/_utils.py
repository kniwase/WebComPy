import asyncio
from collections.abc import Coroutine
from typing import Any, TypeVar

T = TypeVar("T")


def run_sync(coro: Coroutine[Any, Any, T]) -> T:
    """Run a coroutine, handling nested event loops from pytest-asyncio."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    else:
        import nest_asyncio

        if not getattr(loop, "_nest_asyncio_patched", False):
            nest_asyncio.apply(loop)
            loop._nest_asyncio_patched = True  # type: ignore[attr-defined]
        return loop.run_until_complete(coro)
