from argparse import ArgumentParser
import sys
from typing import Any, Literal


def get_params() -> tuple[Literal["start"], dict[str, Any]]:
    def _command(subcommand_name: str):
        return lambda: subcommand_name

    parser = ArgumentParser(prog="python -m webcompy", add_help=True)
    subparsers = parser.add_subparsers()

    # start
    subcommand_name = "start"
    parser_start = subparsers.add_parser(
        subcommand_name,
        help=f"see `{subcommand_name} --help`",
    )
    parser_start.add_argument(
        "--dev",
        action="store_true",
        help="launch dev server",
    )
    parser_start.add_argument(
        "--port",
        type=int,
        help="server port",
    )
    parser_start.set_defaults(__command_getter__=_command(subcommand_name))

    # parse
    args = parser.parse_args()
    if hasattr(args, "__command_getter__"):
        subcommand_name = getattr(args, "__command_getter__")()
        args_dict = {n: getattr(args, n) for n in dir(args) if not n.startswith("_")}
        return subcommand_name, args_dict
    else:
        parser.print_help()
        sys.exit()
