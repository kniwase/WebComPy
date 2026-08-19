from collections.abc import AsyncIterator, Iterator

from webcompy.app import WebComPyApp, WebComPyAppConfig

from .keys import AppThemeKey
from .layout import AppRoot
from .router import router


def _add(a: int, b: int = 0) -> int:
    return a + b


async def _ticker(ticker_id: str, interval: float = 0.1) -> object:
    import asyncio
    import itertools

    for i in itertools.count(1):
        await asyncio.sleep(interval)
        yield {"seq": i}


async def _count_up(n: int, interval: float = 0.05) -> AsyncIterator[int]:
    import asyncio

    for i in range(1, n + 1):
        await asyncio.sleep(interval)
        yield i


def _count_up_sync(n: int) -> Iterator[int]:
    yield from range(1, n + 1)


async def _fail_midway(n: int) -> AsyncIterator[int]:
    for i in range(1, n + 1):
        if i == 3:
            raise RuntimeError("midway failure")
        yield i


app = WebComPyApp(
    root_component=AppRoot,
    router=router,
    config=WebComPyAppConfig(
        base_url="/",
        plugins=["my_app.plugins:ErudaPlugin"],
    ),
)
app.provide(AppThemeKey, "app-dark-theme")
app.rpc.register("add", _add)
app.rpc.register("count_up", _count_up)
app.rpc.register("count_up_sync", _count_up_sync)
app.rpc.register("fail_midway", _fail_midway)
app.rpc.register_subscription("ticker", _ticker)
app.set_head(
    {
        "title": "WebComPy E2E Test",
        "meta": {
            "charset": {
                "charset": "utf-8",
            },
            "viewport": {
                "name": "viewport",
                "content": "width=device-width, initial-scale=1.0",
            },
        },
    }
)
