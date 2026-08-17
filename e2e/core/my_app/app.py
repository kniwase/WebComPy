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
