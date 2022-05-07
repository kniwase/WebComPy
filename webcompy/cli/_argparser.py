from argparse import ArgumentParser
import sys
from typing import Any, Literal


def get_params() -> tuple[Literal["start", "generate", "init"], dict[str, Any]]:
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
    parser_generate.set_defaults(__command_getter__=_command(subcommand_name))

    # init
    subcommand_name = "init"
    parser_init = subparsers.add_parser(
        subcommand_name,
        help="Creates new project on current dir.",
    )
    parser_init.set_defaults(__command_getter__=_command(subcommand_name))

    # parse
    args = parser.parse_args()
    if hasattr(args, "__command_getter__"):
        subcommand_name = getattr(args, "__command_getter__")()
        args_dict = {n: getattr(args, n) for n in dir(args) if not n.startswith("_")}
        return subcommand_name, args_dict
    else:
        parser.print_help()
        sys.exit()
