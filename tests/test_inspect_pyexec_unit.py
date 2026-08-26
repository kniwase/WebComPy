"""Unit tests for the ``webcompy inspect pyexec`` CLI wiring."""

import pytest

from webcompy_cli._inspect import get_inspect_parser
from webcompy_cli._inspect_pyexec import PyexecUsageError, resolve_code_source


def _parse(argv):
    parser = get_inspect_parser()
    return parser.parse_args(["pyexec", *argv])


def test_parser_single_shot_code():
    args = _parse(["print(2+2)"])

    assert args.code == "print(2+2)"
    assert args.file is None
    assert not args.repl
    assert args.repl_timeout == 300
    assert callable(args.func)


def test_parser_file_and_options():
    args = _parse(["--file", "./snippet.py", "--wait-for", "#app", "--repl-timeout", "60"])

    assert args.file == "./snippet.py"
    assert args.wait_for == "#app"
    assert args.repl_timeout == 60


def test_parser_repl_mode():
    args = _parse(["--repl"])

    assert args.repl
    assert args.code is None


def test_resolve_code_from_argument():
    code = resolve_code_source(_parse(["2+2"]))

    assert code == "2+2"


def test_resolve_code_none_in_repl():
    assert resolve_code_source(_parse(["--repl"])) is None


def test_resolve_code_conflicts_raise():
    with pytest.raises(PyexecUsageError) as exc_info:
        resolve_code_source(_parse(["2+2", "--file", "x.py"]))

    assert exc_info.value.code == 2


def test_resolve_code_repl_with_payload_raises():
    with pytest.raises(PyexecUsageError):
        resolve_code_source(_parse(["--repl", "2+2"]))


def test_resolve_code_missing_source_raises():
    with pytest.raises(PyexecUsageError):
        resolve_code_source(_parse([]))


def test_resolve_code_missing_file_raises():
    with pytest.raises(PyexecUsageError):
        resolve_code_source(_parse(["--file", "/nonexistent/nope.py"]))
