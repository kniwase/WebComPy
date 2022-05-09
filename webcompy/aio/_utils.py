from webcompy._browser._modules import browser


async def sleep(delay: float) -> None:
    """Coroutine that completes after a given time (in seconds).

    Args:
        delay (float): seconds
    """
    if browser:
        await browser.aio.sleep(delay)
