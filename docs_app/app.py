from webcompy.app import WebComPyApp, WebComPyAppConfig

from .layout import Root
from .router import router

app = WebComPyApp(
    root_component=Root,
    router=router,
    config=WebComPyAppConfig(base_url="/", plugins=["docs_app.plugins:ErudaPlugin"]),
)
app.set_head(
    {
        "title": "WebComPy - Python Frontend Framework",
        "meta": {
            "charset": {
                "charset": "utf-8",
            },
            "viewport": {
                "name": "viewport",
                "content": "width=device-width, initial-scale=1.0",
            },
            "description": {
                "name": "description",
                "content": "WebComPy is Python frontend framework on Browser",
            },
            "keywords": {
                "name": "keywords",
                "content": "python,framework,browser,frontend,client-side",
            },
            "google-site-verification": {
                "name": "google-site-verification",
                "content": "qRIOGfRioPW7wInrUcunEcZZICOQK1VGZgsP-mlGicA",
            },
        },
        "link": [
            {
                "rel": "stylesheet",
                "href": "/styles/components.css",
            },
        ],
    }
)
