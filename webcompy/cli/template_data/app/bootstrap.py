from webcompy.app import WebComPyApp

from .components.root import Root
from .router import router

app = WebComPyApp(
    root_component=Root,
    router=router,
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
