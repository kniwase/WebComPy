from __future__ import annotations

import json
import os
import pathlib
import signal
import socket
import subprocess
import sys
import time
from argparse import ArgumentParser, Namespace
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from playwright.sync_api import Browser, Page, Playwright

PID_DIR = pathlib.Path(".tmp/webcompy-inspect")

_DEFAULT_WAIT_SECONDS = 5

_CONSOLE_LEVEL_ORDER: dict[str, int] = {
    "off": 0,
    "error": 1,
    "warning": 2,
    "info": 3,
    "log": 4,
    "debug": 5,
}


@dataclass
class ConsoleMessage:
    type: str
    text: str
    location: str

    def format(self) -> str:
        return f"[{self.type}] {self.text} ({self.location})"


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        port = s.getsockname()[1]
    return port


def _check_playwright() -> None:
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401
    except ImportError:
        print(
            "Error: playwright is not installed.\n"
            "Install it with:\n"
            "  uv sync --group dev\n"
            "  uv run playwright install chromium\n"
            "Or:\n"
            "  pip install playwright\n"
            "  playwright install chromium",
            file=sys.stderr,
        )
        sys.exit(1)


def _write_json(data: dict[str, Any]) -> None:
    print(json.dumps(data))


def _write_json_error(message: str) -> None:
    print(json.dumps({"error": message}))


def _ensure_pid_dir() -> None:
    PID_DIR.mkdir(parents=True, exist_ok=True)


def _pid_file_path(port: int) -> pathlib.Path:
    return PID_DIR / f"{port}.pid"


def _read_pid_file(port: int) -> dict[str, Any] | None:
    path = _pid_file_path(port)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data
    except (json.JSONDecodeError, OSError):
        return None


def _write_pid_file(port: int, pid: int, url: str, config_path: str | None) -> None:
    _ensure_pid_dir()
    path = _pid_file_path(port)
    path.write_text(
        json.dumps({"pid": pid, "port": port, "url": url, "config_path": config_path}),
        encoding="utf-8",
    )


def _remove_pid_file(port: int) -> None:
    path = _pid_file_path(port)
    if path.exists():
        path.unlink()


def _is_process_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def _verify_process_identity(pid: int, port: int) -> bool:
    cmdline = _get_process_cmdline(pid)
    if cmdline and "webcompy" in cmdline and "start" in cmdline:
        return True
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            s.connect(("127.0.0.1", port))
            return True
    except OSError:
        return False


def _get_process_cmdline(pid: int) -> str | None:
    try:
        cmdline_path = pathlib.Path(f"/proc/{pid}/cmdline")
        if cmdline_path.exists():
            return cmdline_path.read_bytes().decode(encoding="utf-8", errors="replace").replace("\0", " ")
    except OSError:
        pass
    try:
        result = subprocess.run(
            ["ps", "-p", str(pid), "-o", "command="],
            capture_output=True,
            text=True,
            timeout=2,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        pass
    return None


def cmd_serve(args: Namespace) -> None:
    from webcompy.cli._utils import discover_config

    config_path: str | None = args.config
    dev: bool = args.dev
    port: int = args.port if args.port is not None else 0
    runtime_serving: str | None = args.runtime_serving

    discover_config(config_path)
    actual_config_path = config_path

    if port == 0:
        port = _find_free_port()

    existing_pid = _read_pid_file(port)
    if existing_pid is not None:
        existing_pid_val = existing_pid.get("pid", 0)
        if _is_process_running(existing_pid_val) and _verify_process_identity(existing_pid_val, port):
            _write_json_error(f"Port {port} is already in use by process {existing_pid_val}")
            sys.exit(1)
        _remove_pid_file(port)

    cmd: list[str] = [
        sys.executable,
        "-m",
        "webcompy",
        "start",
        "--port",
        str(port),
    ]
    if config_path:
        cmd.extend(["--config", config_path])
    if dev:
        cmd.append("--dev")
    if runtime_serving:
        cmd.extend(["--runtime-serving", runtime_serving])

    log_file_path = PID_DIR / f"{port}.log"
    _ensure_pid_dir()
    log_file = log_file_path.open("w")
    try:
        proc = subprocess.Popen(cmd, stdout=log_file, stderr=subprocess.STDOUT)
    except Exception as e:
        log_file.close()
        _write_json_error(f"Failed to start server: {e}")
        sys.exit(1)
    finally:
        log_file.close()

    url = f"http://localhost:{port}/"
    _write_pid_file(port, proc.pid, url, actual_config_path)
    _write_json({"port": port, "url": url, "pid": proc.pid})


def cmd_stop(args: Namespace) -> None:
    port: int = args.port
    timeout: int = args.timeout

    pid_data = _read_pid_file(port)
    if pid_data is None:
        _write_json_error(f"No server found on port {port}")
        sys.exit(1)

    pid: int = pid_data.get("pid", 0)

    if not _is_process_running(pid):
        _remove_pid_file(port)
        _write_json({"stopped": False, "port": port, "error": f"No server found on port {port}"})
        sys.exit(1)

    if not _verify_process_identity(pid, port):
        _remove_pid_file(port)
        _write_json({"stopped": False, "port": port, "error": f"Process {pid} on port {port} is not a webcompy server"})
        sys.exit(1)

    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        _remove_pid_file(port)
        _write_json({"stopped": False, "port": port, "error": f"No server found on port {port}"})
        sys.exit(1)

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not _is_process_running(pid):
            break
        time.sleep(0.1)

    if _is_process_running(pid):
        import contextlib

        with contextlib.suppress(ProcessLookupError):
            os.kill(pid, signal.SIGKILL)

    _remove_pid_file(port)
    log_file_path = PID_DIR / f"{port}.log"
    if log_file_path.exists():
        log_file_path.unlink()

    _write_json({"stopped": True, "port": port})


def _launch_browser(
    url: str,
    wait_for: str | None = None,
    on_console: Any | None = None,
) -> tuple[Playwright, Browser, Page]:
    from playwright.sync_api import sync_playwright

    pw = sync_playwright().start()
    browser = pw.chromium.launch(headless=True)
    page = browser.new_page()
    if on_console is not None:
        page.on("console", on_console)
    page.goto(url, wait_until="domcontentloaded")
    if wait_for:
        page.wait_for_selector(wait_for, timeout=30000)
    return pw, browser, page


def _close_browser(pw: Playwright, browser: Browser, page: Page) -> None:
    page.close()
    browser.close()
    pw.stop()


def cmd_screenshot(args: Namespace) -> None:
    _check_playwright()

    url: str = args.url
    selector: str | None = args.selector
    full_page: bool = args.full_page
    output: str | None = args.output
    wait_for: str | None = args.wait_for

    pw, browser, page = _launch_browser(url, wait_for)

    try:
        if selector:
            element = page.query_selector(selector)
            if element is None:
                _write_json_error(f"Element not found: {selector}")
                sys.exit(1)
            screenshot_bytes = element.screenshot()
        else:
            screenshot_bytes = page.screenshot(full_page=full_page)

        if output:
            pathlib.Path(output).write_bytes(screenshot_bytes)
            _write_json({"output": output, "size": len(screenshot_bytes)})
        else:
            import base64

            _write_json({"screenshot": base64.b64encode(screenshot_bytes).decode("ascii")})
    finally:
        _close_browser(pw, browser, page)


def _filter_messages(messages: list[ConsoleMessage], level: str) -> list[ConsoleMessage]:
    min_level = _CONSOLE_LEVEL_ORDER.get(level, 1)
    return [m for m in messages if _CONSOLE_LEVEL_ORDER.get(m.type, 0) <= min_level]


def cmd_console(args: Namespace) -> None:
    _check_playwright()

    url: str = args.url
    level: str = args.level
    wait_ms: int = args.wait
    wait_for: str | None = args.wait_for

    collected: list[ConsoleMessage] = []

    def on_console_msg(msg):
        loc = msg.location if isinstance(msg.location, dict) else {}
        collected.append(
            ConsoleMessage(
                type=msg.type,
                text=msg.text,
                location=f"{loc.get('url', '')}:{loc.get('lineNumber', '')}:{loc.get('columnNumber', '')}",
            )
        )

    pw, browser, page = _launch_browser(url, on_console=on_console_msg)

    try:
        if wait_for:
            page.wait_for_selector(wait_for, timeout=30000)
        time.sleep(wait_ms / 1000)

        filtered = _filter_messages(collected, level)
        _write_json({"messages": [{"type": m.type, "text": m.text, "location": m.location} for m in filtered]})
    finally:
        _close_browser(pw, browser, page)


def cmd_query(args: Namespace) -> None:
    _check_playwright()

    url: str = args.url
    selector: str = args.selector
    property_name: str = args.property
    wait_for: str | None = args.wait_for

    pw, browser, page = _launch_browser(url, wait_for)

    try:
        elements = page.query_selector_all(selector)
        results: list[Any] = []
        for el in elements:
            if property_name == "text":
                results.append(el.text_content())
            elif property_name == "html":
                results.append(el.inner_html())
            elif property_name.startswith("attr:"):
                attr_name = property_name[5:]
                results.append(el.get_attribute(attr_name))
            elif property_name == "visible":
                results.append(el.is_visible())
            elif property_name == "count":
                results.append(len(elements))
                break
            else:
                _write_json_error(f"Unknown property: {property_name}")
                sys.exit(1)

        _write_json({"results": results})
    finally:
        _close_browser(pw, browser, page)


def cmd_click(args: Namespace) -> None:
    _check_playwright()

    url: str = args.url
    selector: str = args.selector
    wait_for: str | None = args.wait_for

    pw, browser, page = _launch_browser(url)

    try:
        element = page.query_selector(selector)
        if element is None:
            _write_json_error(f"Element not found: {selector}")
            sys.exit(1)
        element.click()

        result: dict[str, Any] = {"clicked": True, "selector": selector}

        if wait_for:
            try:
                page.wait_for_selector(wait_for, timeout=10000)
                result["wait_for"] = wait_for
                result["appeared"] = True
            except Exception:
                result["wait_for"] = wait_for
                result["appeared"] = False

        _write_json(result)
    finally:
        _close_browser(pw, browser, page)


def cmd_navigate(args: Namespace) -> None:
    _check_playwright()

    url: str = args.url
    path: str = args.path
    wait_for: str | None = args.wait_for

    pw, browser, page = _launch_browser(url)

    try:
        full_url = url.rstrip("/") + "/" + path.lstrip("/")
        page.goto(full_url, wait_until="domcontentloaded")

        if wait_for:
            page.wait_for_selector(wait_for, timeout=30000)

        _write_json({"current_url": page.url, "title": page.title()})
    finally:
        _close_browser(pw, browser, page)


def _parse_expect(expectation: str) -> tuple[str, str, str]:
    if expectation.startswith("console:"):
        return ("console", expectation, "")

    if ":attr:" in expectation:
        selector, rest = expectation.split(":attr:", 1)
        attr_name, attr_value = rest.split("=", 1)
        return (selector, f"{attr_name}={attr_value}", "attr")

    if expectation.endswith(":visible"):
        selector = expectation[: -len(":visible")]
        return (selector, "visible", "visible")

    if "*=" in expectation:
        selector, text = expectation.split("*=", 1)
        return (selector, text, "contains")

    if "=" in expectation:
        selector, text = expectation.split("=", 1)
        return (selector, text, "exact")

    raise ValueError(f"Invalid expectation format: {expectation}")


def cmd_verify(args: Namespace) -> None:
    _check_playwright()

    url: str = args.url
    expectations: list[str] = args.expect
    wait_for: str | None = args.wait_for

    console_messages: list[ConsoleMessage] = []

    def on_console_msg(msg):
        loc = msg.location if isinstance(msg.location, dict) else {}
        console_messages.append(
            ConsoleMessage(
                type=msg.type,
                text=msg.text,
                location=f"{loc.get('url', '')}:{loc.get('lineNumber', '')}:{loc.get('columnNumber', '')}",
            )
        )

    pw, browser, page = _launch_browser(url, on_console=on_console_msg)

    try:
        if wait_for:
            page.wait_for_selector(wait_for, timeout=30000)
        else:
            time.sleep(_DEFAULT_WAIT_SECONDS)

        passed: list[str] = []
        failed: list[dict[str, Any]] = []

        for expectation in expectations:
            selector, value, kind = _parse_expect(expectation)

            if selector == "console":
                if value == "console:no-error":
                    errors = [m for m in console_messages if m.type == "error"]
                    if not errors:
                        passed.append(expectation)
                    else:
                        failed.append({"expect": expectation, "actual": f"{len(errors)} error(s) found"})
                elif value.startswith("console:no-level="):
                    level = value[len("console:no-level=") :]
                    level_messages = [m for m in console_messages if m.type == level]
                    if not level_messages:
                        passed.append(expectation)
                    else:
                        failed.append(
                            {"expect": expectation, "actual": f"{len(level_messages)} {level} message(s) found"}
                        )
                else:
                    failed.append({"expect": expectation, "actual": f"Unknown console assertion: {value}"})
                continue

            if kind == "visible":
                el = page.query_selector(selector)
                if el and el.is_visible():
                    passed.append(expectation)
                else:
                    failed.append({"expect": expectation, "actual": "element not visible"})
            elif kind == "attr":
                el = page.query_selector(selector)
                if el is None:
                    failed.append({"expect": expectation, "actual": "element not found"})
                    continue
                attr_name, attr_val = value.split("=", 1) if "=" in value else (value, "")
                actual_val = el.get_attribute(attr_name)
                if actual_val == attr_val:
                    passed.append(expectation)
                else:
                    failed.append({"expect": expectation, "actual": f"attr {attr_name}={actual_val}"})
            elif kind == "exact":
                el = page.query_selector(selector)
                if el is None:
                    failed.append({"expect": expectation, "actual": "element not found"})
                    continue
                actual_text = el.text_content()
                if actual_text == value:
                    passed.append(expectation)
                else:
                    failed.append({"expect": expectation, "actual": actual_text})
            elif kind == "contains":
                el = page.query_selector(selector)
                if el is None:
                    failed.append({"expect": expectation, "actual": "element not found"})
                    continue
                actual_text = el.text_content()
                if value in (actual_text or ""):
                    passed.append(expectation)
                else:
                    failed.append({"expect": expectation, "actual": actual_text})

        _write_json({"passed": passed, "failed": failed})
        sys.exit(0 if not failed else 1)
    finally:
        _close_browser(pw, browser, page)


def get_inspect_parser() -> ArgumentParser:
    parser = ArgumentParser(
        prog="python -m webcompy inspect",
        description="Inspect a WebComPy application in a browser",
    )
    subparsers = parser.add_subparsers(dest="inspect_command")

    serve_parser = subparsers.add_parser("serve", help="Launch a WebComPy app server")
    serve_parser.add_argument("--config", type=str, help="Python import path for config module")
    serve_parser.add_argument("--dev", action="store_true", help="Enable hot-reload mode")
    serve_parser.add_argument("--port", type=int, default=None, help="Port number (0 for auto-detect)")
    serve_parser.add_argument("--runtime-serving", choices=["cdn", "local"], default=None, help="Runtime serving mode")
    serve_parser.set_defaults(func=cmd_serve)

    stop_parser = subparsers.add_parser("stop", help="Stop a running WebComPy app server")
    stop_parser.add_argument("port", type=int, help="Port number of the server to stop")
    stop_parser.add_argument("--timeout", type=int, default=10, help="Timeout in seconds (default: 10)")
    stop_parser.set_defaults(func=cmd_stop)

    screenshot_parser = subparsers.add_parser("screenshot", help="Capture a screenshot of a URL")
    screenshot_parser.add_argument("url", type=str, help="URL to screenshot")
    screenshot_parser.add_argument("--selector", type=str, default=None, help="CSS selector for element screenshot")
    screenshot_parser.add_argument("--full-page", action="store_true", help="Capture the full scrollable page")
    screenshot_parser.add_argument(
        "--output", type=str, default=None, help="Output file path (default: base64 to stdout)"
    )
    screenshot_parser.add_argument(
        "--wait-for", type=str, default=None, help="CSS selector to wait for before capturing"
    )
    screenshot_parser.set_defaults(func=cmd_screenshot)

    console_parser = subparsers.add_parser("console", help="Collect browser console messages")
    console_parser.add_argument("url", type=str, help="URL to inspect")
    console_parser.add_argument(
        "--level",
        type=str,
        default="warning",
        choices=list(_CONSOLE_LEVEL_ORDER.keys())[1:],
        help="Minimum console level to include (default: warning)",
    )
    console_parser.add_argument(
        "--wait", type=int, default=5000, help="Collection duration in milliseconds (default: 5000)"
    )
    console_parser.add_argument("--wait-for", type=str, default=None, help="CSS selector to wait for before collecting")
    console_parser.set_defaults(func=cmd_console)

    query_parser = subparsers.add_parser("query", help="Query DOM element properties")
    query_parser.add_argument("url", type=str, help="URL to inspect")
    query_parser.add_argument("selector", type=str, help="CSS selector to query")
    query_parser.add_argument(
        "--property",
        type=str,
        default="text",
        help="Property to retrieve: text, html, attr:NAME, visible, count (default: text)",
    )
    query_parser.add_argument("--wait-for", type=str, default=None, help="CSS selector to wait for before querying")
    query_parser.set_defaults(func=cmd_query)

    click_parser = subparsers.add_parser("click", help="Click an element in the browser")
    click_parser.add_argument("url", type=str, help="URL to navigate to")
    click_parser.add_argument("selector", type=str, help="CSS selector of element to click")
    click_parser.add_argument("--wait-for", type=str, default=None, help="CSS selector to wait for after clicking")
    click_parser.set_defaults(func=cmd_click)

    navigate_parser = subparsers.add_parser("navigate", help="Navigate to a path within the app")
    navigate_parser.add_argument("url", type=str, help="Base URL to navigate to")
    navigate_parser.add_argument("path", type=str, help="Path to navigate to within the app")
    navigate_parser.add_argument("--wait-for", type=str, default=None, help="CSS selector to wait for after navigation")
    navigate_parser.set_defaults(func=cmd_navigate)

    verify_parser = subparsers.add_parser("verify", help="Verify expectations about a page")
    verify_parser.add_argument("url", type=str, help="URL to verify")
    verify_parser.add_argument(
        "--expect",
        action="append",
        default=[],
        help="Expectation: selector=text, selector*=text, selector:visible, selector:attr:name=value, console:no-error, console:no-level=LEVEL. Use :attr: for selectors containing =",
    )
    verify_parser.add_argument("--wait-for", type=str, default=None, help="CSS selector to wait for before checking")
    verify_parser.set_defaults(func=cmd_verify)

    return parser


def run_inspect() -> None:
    parser = get_inspect_parser()
    args = parser.parse_args(sys.argv[2:])
    if not hasattr(args, "func") or args.func is None:
        parser.print_help()
        sys.exit(1)
    args.func(args)
