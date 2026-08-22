import asyncio


async def sleep(delay: float) -> None:
    """Coroutine that completes after a given time (in seconds).

    Args:
        delay: seconds to wait.

    """
    await asyncio.sleep(delay)
