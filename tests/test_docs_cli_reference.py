from __future__ import annotations

import re
from argparse import ArgumentParser, Namespace, _SubParsersAction
from pathlib import Path
from unittest.mock import patch

from webcompy_cli._argparser import get_params
from webcompy_cli._inspect import get_inspect_parser

CLI_DOC = Path(__file__).parent.parent / "docs_app" / "documents" / "server_cli_reference.md"
_FLAG_RE = re.compile(r"(?<!-)--[a-z][a-z0-9-]*")
_TOP_SUBCOMMAND_ROW_RE = re.compile(r"^\|\s*`python -m webcompy ([a-z][a-z0-9-]*)`\s*\|", re.MULTILINE)
_INSPECT_SUBCOMMAND_ROW_RE = re.compile(r"^\|\s*`([a-z][a-z0-9-]*)`\s*\|\s*(?:—|`[^|]+`)\s*\|", re.MULTILINE)
_INSPECT_SUBHEADING_RE = re.compile(r"^### .*`([a-z][a-z0-9-]*)`$", re.MULTILINE)


def _capture_main_parser() -> ArgumentParser:
    captured: list[ArgumentParser] = []

    def _fake_parse_args(self: ArgumentParser, *args: object, **kwargs: object) -> Namespace:
        captured.append(self)
        return Namespace(__command_getter__=lambda: "start")

    with patch.object(ArgumentParser, "parse_args", _fake_parse_args):
        get_params()
    assert len(captured) == 1
    return captured[0]


def _subparsers_map(parser: ArgumentParser) -> dict[str, ArgumentParser]:
    for action in parser._actions:
        if isinstance(action, _SubParsersAction) and isinstance(action.choices, dict):
            return dict(action.choices)
    raise AssertionError("No subparsers registered on ArgumentParser")


def _long_flags(parser: ArgumentParser) -> set[str]:
    return {opt for opt in parser._option_string_actions if opt.startswith("--")}


def test_documented_top_level_subcommands_match_parser() -> None:
    text = CLI_DOC.read_text(encoding="utf-8")
    main_parser = _capture_main_parser()
    parser_subcommands = set(_subparsers_map(main_parser))
    doc_subcommands = set(_TOP_SUBCOMMAND_ROW_RE.findall(text))
    assert doc_subcommands == parser_subcommands


def test_documented_inspect_subcommands_match_parser() -> None:
    text = CLI_DOC.read_text(encoding="utf-8")
    inspect_section = text.split("## Inspect subcommands", 1)[1].split("## Exit codes", 1)[0]
    inspect_parser = get_inspect_parser()
    parser_subcommands = set(_subparsers_map(inspect_parser))
    doc_subcommands = set(_INSPECT_SUBCOMMAND_ROW_RE.findall(inspect_section)) | set(
        _INSPECT_SUBHEADING_RE.findall(inspect_section)
    )
    assert doc_subcommands == parser_subcommands


def test_documented_flags_match_parsers() -> None:
    text = CLI_DOC.read_text(encoding="utf-8")
    main_subparsers = _subparsers_map(_capture_main_parser())
    inspect_subparsers = _subparsers_map(get_inspect_parser())

    all_parser_flags: set[str] = set()
    for sub_parser in [*main_subparsers.values(), *inspect_subparsers.values()]:
        all_parser_flags.update(_long_flags(sub_parser))

    doc_flags = set(_FLAG_RE.findall(text))
    assert doc_flags <= all_parser_flags | {"--help"}
    assert (all_parser_flags - {"--help"}) <= doc_flags

    start_section = text.split("### `start`", 1)[1].split("### `generate`", 1)[0]
    generate_section = text.split("### `generate`", 1)[1].split("### `init`", 1)[0]
    lock_section = text.split("### `lock`", 1)[1].split("## Inspect subcommands", 1)[0]
    inspect_section = text.split("## Inspect subcommands", 1)[1].split("## Exit codes", 1)[0]

    assert (set(_FLAG_RE.findall(start_section)) - {"--help"}) == (_long_flags(main_subparsers["start"]) - {"--help"})
    assert (set(_FLAG_RE.findall(generate_section)) - {"--help"}) == (
        _long_flags(main_subparsers["generate"]) - {"--help"}
    )
    assert (set(_FLAG_RE.findall(lock_section)) - {"--help"}) == (_long_flags(main_subparsers["lock"]) - {"--help"})

    inspect_flags: set[str] = set()
    for sub_parser in inspect_subparsers.values():
        inspect_flags.update(_long_flags(sub_parser))
    assert (set(_FLAG_RE.findall(inspect_section)) - {"--help"}) == (inspect_flags - {"--help"})
