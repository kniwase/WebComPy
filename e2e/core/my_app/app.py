from collections.abc import AsyncIterator, Iterator

from webcompy.app import WebComPyApp, WebComPyAppConfig

from .keys import AppThemeKey
from .layout import AppRoot
from .router import router
from .rpc_schema import AddParams, CountUpParams, TickerParams, add, count_up, count_up_sync, fail_midway, ticker


def _add(p: AddParams) -> int:
    return p.a + p.b


async def _ticker(p: TickerParams) -> AsyncIterator[dict]:
    import asyncio
    import itertools

    for i in itertools.count(1):
        await asyncio.sleep(0.1)
        yield {"seq": i}


async def _count_up(p: CountUpParams) -> AsyncIterator[int]:
    import asyncio

    for i in range(1, p.n + 1):
        await asyncio.sleep(0.05)
        yield i


def _count_up_sync(p: CountUpParams) -> Iterator[int]:
    yield from range(1, p.n + 1)


async def _fail_midway(p: CountUpParams) -> AsyncIterator[int]:
    for i in range(1, p.n + 1):
        if i == 3:
            raise RuntimeError("midway failure")
        yield i


app = WebComPyApp(
    root_component=AppRoot,
    router=router,
    config=WebComPyAppConfig(
        base_url="/",
        plugins=[
            "my_app.plugins:ErudaPlugin",
            "my_app.plugins:MockFetchPlugin",
            "my_app.plugins:MockRpcPlugin",
        ],
    ),
)
app.provide(AppThemeKey, "app-dark-theme")
app.rpc.bind(add, _add)
app.rpc.bind(count_up, _count_up)
app.rpc.bind(count_up_sync, _count_up_sync)
app.rpc.bind(fail_midway, _fail_midway)
app.rpc.bind(ticker, _ticker)
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
