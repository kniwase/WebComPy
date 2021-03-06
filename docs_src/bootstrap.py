from webcompy.app import WebComPyApp
from .router import router
from .layout import Root


app = WebComPyApp(
    root_component=Root,
    router=router,
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
                "href": "https://cdn.jsdelivr.net/npm/bootstrap@5.0.2/dist/css/bootstrap.min.css",
                "integrity": "sha384-EVSTQN3/azprG1Anm3QDgpJLIm9Nao0Yz1ztcQTwFspd3yD65VohhpuuCOmLASjC",
                "crossorigin": "anonymous",
            },
            {
                "rel": "stylesheet",
                "href": "https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.5.1/styles/default.min.css",
            },
        ],
    }
)
app.append_script(
    {
        "type": "text/javascript",
        "src": "https://cdnjs.cloudflare.com/ajax/libs/eruda/2.4.1/eruda.min.js",
    },
    in_head=True,
)
app.append_script(
    {"type": "text/javascript"},
    script="eruda.init();",
)
app.append_script(
    {
        "type": "text/javascript",
        "src": "https://cdn.jsdelivr.net/npm/bootstrap@5.0.2/dist/js/bootstrap.bundle.min.js",
        "integrity": "sha384-MrcW6ZMFYlzcLA8Nl+NtUVF0sA7MsXsP1UyJoMp4YLEuNSfAP+JcXn/tWtIaxVXM",
        "crossorigin": "anonymous",
    },
)
app.append_script(
    {
        "type": "text/javascript",
        "src": "https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.5.1/highlight.min.js",
    },
)
