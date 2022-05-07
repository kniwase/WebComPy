from webcompy.cli._server import create_asgi_app
from webcompy.cli._utils import get_config
from webcompy.cli._argparser import get_params

config = get_config()
_, args = get_params()
app = create_asgi_app(config, args["dev"])
