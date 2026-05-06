from pathlib import Path

from webcompy.app import AppConfig, PluginScript, WebComPyApp

from .keys import AppThemeKey
from .layout import Root
from .router import router

app = WebComPyApp(
    root_component=Root,
    router=router,
    config=AppConfig(
        app_package=Path(__file__).parent,
        base_url="/",
        dependencies=["aiofiles"],
        scripts=[
            PluginScript(
                attrs={
                    "type": "text/javascript",
                    "src": "https://cdnjs.cloudflare.com/ajax/libs/eruda/2.4.1/eruda.min.js",
                },
                script="eruda.init();",
                in_head=True,
                condition="new URLSearchParams(location.search).get('debug') === 'True'",
            ),
        ],
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
