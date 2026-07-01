import sys


def main():
    try:
        from webcompy_cli._argparser import get_params
        from webcompy_cli._generate import generate_static_site
        from webcompy_cli._init_project import init_project
        from webcompy_cli._inspect import run_inspect
        from webcompy_cli._lock import lock_command
        from webcompy_cli._server import run_server
    except ImportError:
        print(
            "webcompy-cli is not installed. Install with: pip install webcompy[cli]",
            file=sys.stderr,
        )
        sys.exit(1)

    if len(sys.argv) > 1 and sys.argv[1] == "inspect":
        run_inspect()
        return

    import asyncio

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
