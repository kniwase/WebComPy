from starlette.applications import Starlette
from starlette.routing import Mount

from webcompy.cli._argparser import get_params
from webcompy.cli._server import create_asgi_app
from webcompy.cli._utils import get_app, get_config

config = get_config()
_, args = get_params()
app = get_app(config)
asgi_app = Starlette(
    routes=[
        Mount(
            config.base,
            create_asgi_app(app, config, args["dev"]),
        )
    ]
)
