import sys
from argparse import ArgumentParser
from typing import Any, Literal


def get_params() -> tuple[Literal["start", "generate", "init", "lock"], dict[str, Any]]:
    def _command(subcommand_name: str):
        return lambda: subcommand_name

    maincommand = "python -m webcompy"
    parser = ArgumentParser(prog=maincommand, add_help=True)
    subparsers = parser.add_subparsers()

    # start
    subcommand_name = "start"
    parser_start = subparsers.add_parser(
        subcommand_name,
        help=f"Starts HTTP server. See `{maincommand} {subcommand_name} --help` for options.",
    )
    parser_start.add_argument(
        "--dev",
        action="store_true",
        help="launch dev server with hot-reload",
    )
    parser_start.add_argument(
        "--port",
        type=int,
        help="server port",
    )
    parser_start.add_argument(
        "--app",
        type=str,
        help="import path for app instance (e.g., my_app.bootstrap:app)",
    )
    parser_start.set_defaults(__command_getter__=_command(subcommand_name))

    # generate
    subcommand_name = "generate"
    parser_generate = subparsers.add_parser(
        subcommand_name,
        help=f"Generates static html files. See `{maincommand} {subcommand_name} --help` for options.",
    )
    parser_generate.add_argument(
        "--dist",
        type=str,
        help="dist dir",
    )
    parser_generate.add_argument(
        "--app",
        type=str,
        help="import path for app instance (e.g., my_app.bootstrap:app)",
    )
    parser_generate.set_defaults(__command_getter__=_command(subcommand_name))

    # init
    subcommand_name = "init"
    parser_init = subparsers.add_parser(
        subcommand_name,
        help="Creates new project on current dir.",
    )
    parser_init.set_defaults(__command_getter__=_command(subcommand_name))

    # lock
    subcommand_name = "lock"
    parser_lock = subparsers.add_parser(
        subcommand_name,
        help="Generates or updates webcompy-lock.json.",
    )
    parser_lock.add_argument(
        "--app",
        type=str,
        help="import path for app instance (e.g., my_app.bootstrap:app)",
    )
    lock_flags = parser_lock.add_mutually_exclusive_group()
    lock_flags.add_argument(
        "--export",
        action="store_true",
        help="Export lock file dependencies to requirements.txt",
    )
    lock_flags.add_argument(
        "--sync",
        action="store_true",
        help="Compare lock file with requirements.txt/pyproject.toml",
    )
    lock_flags.add_argument(
        "--install",
        action="store_true",
        help="Export and install lock file dependencies",
    )
    parser_lock.set_defaults(__command_getter__=_command(subcommand_name))

    # parse
    args = parser.parse_args()
    if hasattr(args, "__command_getter__"):
        subcommand_name = args.__command_getter__()
        args_dict = {n: getattr(args, n) for n in dir(args) if not n.startswith("_")}
        return subcommand_name, args_dict
    else:
        parser.print_help()
        sys.exit()
