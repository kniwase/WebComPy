"""``webcompy inspect pyexec``: evaluate Python code in a harness PyScript interpreter.

Launches a single browser-harness session (the same boot path as the browser
test tier), evaluates the given code through the in-page ``evaluate``
gateway, and prints a structured JSON result. With ``--repl``, the session
stays alive and each stdin line is evaluated in turn, preserving interpreter
state. Evaluation is confined to the harness interpreter; it never targets a
production ``webcompy start`` server process.
"""

from __future__ import annotations

import contextlib
import json
import queue
import signal
import sys
import threading
from argparse import Namespace
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from playwright.sync_api import Page

_READY_SENTINEL_SELECTOR = "html[data-webcompy-test-ready='1']"
_READY_TIMEOUT_SECONDS = 120.0
_DEFAULT_REPL_TIMEOUT_SECONDS = 300


class PyexecUsageError(SystemExit):
    """Raised for invalid ``pyexec`` argument combinations (exit code 2)."""

    def __init__(self, message: str) -> None:
        super().__init__(2)
        print(f"usage error: {message}", file=sys.stderr)


def register_pyexec_parser(subparsers: Any) -> None:
    """Register the ``pyexec`` sub-subcommand on the ``inspect`` parser.

    Args:
        subparsers: The ``inspect`` command's subparsers action.

    """
    parser = subparsers.add_parser(
        "pyexec",
        help="Evaluate Python code inside a real PyScript interpreter",
        description=(
            "Evaluate Python code inside a real PyScript interpreter served by the "
            "local browser test harness and print a structured JSON result."
        ),
    )
    parser.add_argument("code", nargs="?", default=None, help="Python code to evaluate")
    parser.add_argument("--file", default=None, help="Read the code from this file instead of CODE")
    parser.add_argument(
        "--repl",
        action="store_true",
        help="Keep the session alive; evaluate one stdin line per turn until EOF",
    )
    parser.add_argument(
        "--repl-timeout",
        type=int,
        default=_DEFAULT_REPL_TIMEOUT_SECONDS,
        help=f"REPL idle timeout in seconds (default: {_DEFAULT_REPL_TIMEOUT_SECONDS})",
    )
    parser.add_argument("--wait-for", dest="wait_for", default=None, help="CSS selector to wait for before evaluating")
    parser.set_defaults(func=cmd_pyexec)


def resolve_code_source(args: Namespace) -> str | None:
    """Resolve the code payload from CODE / --file for single-shot evaluation.

    Args:
        args: Parsed ``pyexec`` arguments.

    Returns:
        The code string to evaluate, or ``None`` in REPL mode.

    Raises:
        PyexecUsageError: On mutually exclusive or missing code sources, or
            when ``--file`` does not exist.

    """
    if args.repl:
        if args.code is not None or args.file is not None:
            raise PyexecUsageError("--repl cannot be combined with CODE or --file")
        return None
    if args.code is not None and args.file is not None:
        raise PyexecUsageError("CODE and --file are mutually exclusive")
    if args.file is not None:
        path = Path(args.file)
        if not path.is_file():
            raise PyexecUsageError(f"--file does not exist: {path}")
        return path.read_text(encoding="utf-8")
    if args.code is not None:
        return args.code
    raise PyexecUsageError("provide CODE, --file <path>, or --repl")


class _PyexecSession:
    """One harness server plus one Playwright page bound to its lifetime."""

    def __init__(self, wait_for: str | None = None) -> None:
        from playwright.sync_api import sync_playwright

        from webcompy_cli._browser_test_harness import create_harness_app, reserve_port, serve_harness

        repo_root = Path.cwd()
        cache_dir = repo_root / ".tmp" / "webcompy-browser-harness"
        cache_dir.mkdir(parents=True, exist_ok=True)
        port = reserve_port()
        base_url = f"http://127.0.0.1:{port}/"
        self._harness = create_harness_app(repo_root, cache_dir, base_url=base_url)
        self._process = serve_harness(self._harness, port=port)
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch(headless=True)
        page = self._browser.new_page()
        try:
            page.goto(f"{base_url.rstrip('/')}/testharness", wait_until="domcontentloaded")
            timeout_ms = int(_READY_TIMEOUT_SECONDS * 1000)
            page.wait_for_selector(_READY_SENTINEL_SELECTOR, state="attached", timeout=timeout_ms)
        except Exception as e:
            self.close()
            tail = "see harness console output above"
            raise RuntimeError(
                f"harness page did not become ready within {_READY_TIMEOUT_SECONDS:.0f}s ({tail})"
            ) from e
        if wait_for:
            page.wait_for_selector(wait_for, timeout=30000)
        self._page: Page = page

    def evaluate(self, code: str) -> dict[str, Any]:
        """Evaluate code through the in-page gateway and return its JSON payload.

        Args:
            code: Python source to evaluate.

        Returns:
            The parsed result payload with ``stdout``, ``stderr``,
            ``result_repr``, ``console_error_delta``, ``exc_type``, and
            ``traceback`` keys.

        """
        raw = self._page.evaluate("c => window.__webcompy_test__.evaluate(c)", code)
        if isinstance(raw, (str, bytes)):
            return json.loads(raw)
        return raw

    def close(self) -> None:
        """Tear down the page, browser, Playwright driver, and harness server."""
        from contextlib import suppress

        with suppress(Exception):
            self._page.close()
        with suppress(Exception):
            self._browser.close()
        with suppress(Exception):
            self._pw.stop()
        with suppress(Exception):
            from webcompy_cli._browser_test_harness import shutdown_harness

            shutdown_harness(self._process)


def cmd_pyexec(args: Namespace) -> None:
    """Run the ``pyexec`` subcommand (single-shot or REPL).

    Args:
        args: Parsed arguments carrying ``code``, ``file``, ``repl``,
            ``repl_timeout``, and ``wait_for``.

    """
    from webcompy_cli._inspect import _check_playwright

    _check_playwright()
    code_source = resolve_code_source(args)

    # Keep stdout clean: only JSON goes to stdout, harness logs go to stderr.
    with contextlib.redirect_stdout(sys.stderr):
        session = _PyexecSession(wait_for=args.wait_for)
    try:
        if args.repl:
            sys.exit(_run_repl(session, args.repl_timeout))
        print(json.dumps(session.evaluate(code_source or "")))
    finally:
        session.close()


def _run_repl(session: _PyexecSession, repl_timeout: int) -> int:
    """Loop stdin lines through :meth:`_PyexecSession.evaluate`.

    Each evaluated line prints one compact JSON object on its own line.
    EOF (Ctrl-D) exits cleanly; SIGINT tears the session down; exceeding the
    idle timeout exits with code 124.

    Args:
        session: The live harness session to evaluate against.
        repl_timeout: Idle timeout in seconds between input lines.

    Returns:
        Process exit code: 0 on EOF, 130 on SIGINT, 124 on idle timeout.

    """
    lines: queue.Queue[str | None] = queue.Queue()

    def read_stdin() -> None:
        try:
            for line in sys.stdin:
                lines.put(line.rstrip("\n"))
        finally:
            lines.put(None)

    reader = threading.Thread(target=read_stdin, daemon=True)
    reader.start()

    interrupted = False

    def on_sigint(signum, frame):
        nonlocal interrupted
        interrupted = True
        lines.put(None)

    previous_sigint = signal.getsignal(signal.SIGINT)
    signal.signal(signal.SIGINT, on_sigint)
    exit_code = 0
    try:
        while True:
            try:
                line = lines.get(timeout=repl_timeout)
            except queue.Empty:
                print(json.dumps({"error": f"idle timeout after {repl_timeout}s"}), flush=True)
                exit_code = 124
                break
            if line is None:
                if interrupted:
                    exit_code = 130
                break
            if not line.strip():
                continue
            print(json.dumps(session.evaluate(line)), flush=True)
    finally:
        signal.signal(signal.SIGINT, previous_sigint)
    return exit_code
