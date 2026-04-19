from webcompy.app import AppConfig, WebComPyApp

from .components.root import Root
from .router import router

app = WebComPyApp(
    root_component=Root,
    router=router,
    config=AppConfig(app_package=__package__),
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
