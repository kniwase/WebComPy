from webcompy.app import WebComPyApp
from .router import router
from .components.root import Root

app = WebComPyApp(
    root_component=Root,
    router=router,
)
app.set_head(
    {
        "title": "WebComPy Template",
        "meta": [
            {"charset": "utf-8"},
        ],
    }
)
