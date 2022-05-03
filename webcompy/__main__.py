from webcompy.cli._argparser import get_params
from webcompy.cli._server import run_server

command, _ = get_params()

if command == "start":
    run_server()
