from webcompy.app import WebComPyApp

from .keys import AppThemeKey
from .layout import Root
from .router import router

app = WebComPyApp(
    root_component=Root,
    router=router,
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
