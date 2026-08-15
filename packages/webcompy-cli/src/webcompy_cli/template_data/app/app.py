from webcompy.app import WebComPyApp, WebComPyAppConfig

from .components.root import AppRoot
from .router import router

app = WebComPyApp(
    root_component=AppRoot,
    router=router,
    config=WebComPyAppConfig(base_url="/"),
)
app.set_head(
    {
        "title": "WebComPy Template",
        "meta": {
            "charset": {
                "charset": "utf-8",
            },
        },
    }
)
