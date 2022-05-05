from webcompy.cli._argparser import get_params
from webcompy.cli._server import run_server
from webcompy.cli._generate import generate_static_site


def main():
    command, _ = get_params()
    if command == "start":
        run_server()
    elif command == "generate":
        generate_static_site()


if __name__ == "__main__":
    main()
