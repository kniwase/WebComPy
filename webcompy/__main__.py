import asyncio
import sys

from webcompy.cli._argparser import get_params
from webcompy.cli._generate import generate_static_site
from webcompy.cli._init_project import init_project
from webcompy.cli._inspect import run_inspect
from webcompy.cli._lock import lock_command
from webcompy.cli._server import run_server


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "inspect":
        run_inspect()
        return

    command, _ = get_params()
    if command == "start":
        run_server()
    elif command == "generate":
        asyncio.run(generate_static_site())
    elif command == "init":
        init_project()
    elif command == "lock":
        lock_command()


if __name__ == "__main__":
    main()
