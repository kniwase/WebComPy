from webcompy.cli._argparser import get_params
from webcompy.cli._generate import generate_static_site
from webcompy.cli._init_project import init_project
from webcompy.cli._lock import lock_command
from webcompy.cli._server import run_server


def main():
    command, _ = get_params()
    if command == "start":
        run_server()
    elif command == "generate":
        generate_static_site()
    elif command == "init":
        init_project()
    elif command == "lock":
        lock_command()


if __name__ == "__main__":
    main()
