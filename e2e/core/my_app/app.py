from webcompy.app import WebComPyApp, WebComPyAppConfig

from .keys import AppThemeKey
from .layout import Root
from .router import router

app = WebComPyApp(
    root_component=Root,
    router=router,
    config=WebComPyAppConfig(
        base_url="/",
        plugins=["my_app.plugins:ErudaPlugin"],
    ),
)
app.provide(AppThemeKey, "app-dark-theme")
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
