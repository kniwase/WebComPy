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

        nest_asyncio.apply(loop)
        return loop.run_until_complete(coro)


async def sleep(delay: float) -> None:
    """Coroutine that completes after a given time (in seconds).

    Args:
        delay (float): seconds
    """
    await asyncio.sleep(delay)
