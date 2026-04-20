from webcompy.app import WebComPyApp
from webcompy_config import app_config

from .components.root import Root
from .router import router

app = WebComPyApp(
    root_component=Root,
    router=router,
    config=app_config,
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
