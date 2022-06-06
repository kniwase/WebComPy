from starlette.applications import Starlette
from starlette.routing import Mount
from webcompy.cli._server import create_asgi_app
from webcompy.cli._utils import get_config, get_app
from webcompy.cli._argparser import get_params

config = get_config()
_, args = get_params()
app = Starlette(
    routes=[
        Mount(
            config.base,
            create_asgi_app(get_app(config), config, args["dev"]),
        )
    ]
)
