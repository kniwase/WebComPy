from __future__ import annotations

import os
import pathlib
import shutil
import subprocess
import threading
import time
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from functools import partial
from http.server import HTTPServer, SimpleHTTPRequestHandler
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from playwright.sync_api import Page

PROJECT_ROOT = pathlib.Path(__file__).parent.parent.parent
E2E_DIR = pathlib.Path(__file__).parent
PORT = int(os.environ.get("E2E_PORT", "8088"))
BASE_URL = f"http://localhost:{PORT}/"
PYSCRIPT_INIT_TIMEOUT = 120_000
PYSCRIPT_POLL_INTERVAL = 500
SERVER_LOG = pathlib.Path(os.environ.get("E2E_SERVER_LOG", str(pathlib.Path(__file__).parent / ".e2e-server.log")))
TMP_DIR = pathlib.Path(
    os.environ.get("E2E_TMP_DIR", str(pathlib.Path(__file__).parent.parent.parent / ".tmp" / "e2e-static"))
)

_PYTHON_TRACEBACK_PATTERNS = (
    "Traceback (most recent call last):",
    "micropip._vendored.",
    "pyodide.",
)

_ASSET_ERROR_PATTERNS = (
    "Failed to load resource",
    "Failed to find a valid digest",
    "integrity",
    "Failed to fetch",
    "ModuleNotFoundError",
)

_CONSOLE_LEVEL_ORDER = {"off": 0, "error": 1, "warning": 2, "info": 3, "log": 4, "debug": 5}


def _parse_console_level(value: str | None, default: str) -> str:
    if value is None:
        return default
    if value not in _CONSOLE_LEVEL_ORDER:
        raise ValueError(f"Invalid console level: {value!r}. Expected one of: {', '.join(_CONSOLE_LEVEL_ORDER)}")
    return value


CONSOLE_FILE_LEVEL = _parse_console_level(os.environ.get("CONSOLE_FILE_LEVEL"), "debug")
CONSOLE_STDOUT_LEVEL = _parse_console_level(os.environ.get("CONSOLE_STDOUT_LEVEL"), "warning")
CONSOLE_LOG_DIR = os.environ.get("CONSOLE_LOG_DIR")


@dataclass
class ConsoleMessage:
    type: str
    text: str
    location: str

    def format(self) -> str:
        return f"[{self.type}] {self.text} ({self.location})"


def _collect_console_messages(page: Page, messages: list[ConsoleMessage]):
    def on_console_msg(msg):
        loc = msg.location if isinstance(msg.location, dict) else {}
        messages.append(
            ConsoleMessage(
                type=msg.type,
                text=msg.text,
                location=f"{loc.get('url', '')}:{loc.get('lineNumber', '')}:{loc.get('columnNumber', '')}",
            )
        )

    page.on("console", on_console_msg)


class _QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        resolved = self.translate_path(self.path.split("?")[0])
        if pathlib.Path(resolved).is_file():
            super().do_GET()
        elif (pathlib.Path(resolved) / "index.html").is_file():
            self.path = self.path.rstrip("/") + "/index.html"
            super().do_GET()
        else:
            fallback = pathlib.Path(self.directory) / "404.html"
            if fallback.is_file():
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(fallback.read_bytes())
            else:
                self.send_response(404)
                self.end_headers()


def pytest_addoption(parser):
    parser.addoption(
        "--serving-mode",
        action="store",
        default=None,
        choices=["prod", "static"],
        help="Run E2E tests against a single serving mode (prod or static)",
    )


def pytest_generate_tests(metafunc):
    if "serving_mode" in metafunc.fixturenames:
        option = metafunc.config.getoption("--serving-mode")
        if option is not None:
            metafunc.parametrize("serving_mode", [option], ids=[option])
        else:
            metafunc.parametrize("serving_mode", ["prod", "static"], ids=["prod", "static"])


def pytest_configure(config):
    config.addinivalue_line("markers", "e2e: End-to-end tests requiring a browser and server")


def _check_asset_errors(messages: list[ConsoleMessage]):
    asset_errors = [m for m in messages if m.type == "error" and any(p in m.text for p in _ASSET_ERROR_PATTERNS)]
    if asset_errors:
        pytest.exit(
            f"Asset loading errors detected ({len(asset_errors)}) — aborting all tests:\n"
            + "\n---\n".join(m.format() for m in asset_errors)
        )


def _check_python_errors(messages: list[ConsoleMessage]):
    python_errors = [m for m in messages if m.type == "error" and any(p in m.text for p in _PYTHON_TRACEBACK_PATTERNS)]
    if python_errors:
        pytest.fail(
            f"Python errors detected during initialization ({len(python_errors)}):\n"
            + "\n---\n".join(m.format() for m in python_errors[:5])
        )


def _wait_for_pyscript_init(page: Page, console_messages_list: list[ConsoleMessage]):
    start_time = time.monotonic()
    while True:
        _check_asset_errors(console_messages_list)
        _check_python_errors(console_messages_list)
        try:
            page.wait_for_selector("#webcompy-loading", state="hidden", timeout=PYSCRIPT_POLL_INTERVAL)
        except Exception:
            pass
        else:
            page.wait_for_selector("#webcompy-app:not([hidden])", timeout=PYSCRIPT_POLL_INTERVAL)
            return
        if time.monotonic() - start_time > PYSCRIPT_INIT_TIMEOUT / 1000:
            remaining = console_messages_list[-5:] if console_messages_list else []
            pytest.fail(
                f"PyScript did not initialize within {PYSCRIPT_INIT_TIMEOUT / 1000:.0f}s\n"
                + f"Last console messages: {[m.format() for m in remaining]}"
            )


@pytest.fixture(scope="session")
def prod_server():
    env = os.environ.copy()
    env["PYTHONPATH"] = str(E2E_DIR) + os.pathsep + env.get("PYTHONPATH", "")

    log_file = SERVER_LOG.open("w")
    proc = subprocess.Popen(
        [
            "uv",
            "run",
            "--project",
            str(PROJECT_ROOT),
            "python",
            "-m",
            "webcompy",
            "start",
            "--port",
            str(PORT),
        ],
        cwd=str(E2E_DIR),
        stdout=log_file,
        stderr=subprocess.STDOUT,
        env=env,
    )

    for _ in range(120):
        try:
            urllib.request.urlopen(BASE_URL, timeout=5)
            break
        except Exception:
            if proc.poll() is not None:
                log_file.close()
                log_content = SERVER_LOG.read_text()
                pytest.fail(f"Server exited prematurely (code {proc.returncode}):\n{log_content}")
            time.sleep(1)
    else:
        log_file.close()
        log_content = SERVER_LOG.read_text()
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)
        pytest.fail(f"Server did not start within 120 seconds:\n{log_content}")

    yield proc

    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=5)
    finally:
        log_file.close()


@pytest.fixture(scope="session")
def static_site():
    app_dir = E2E_DIR / "my_app"

    if TMP_DIR.exists():
        shutil.rmtree(TMP_DIR)
    TMP_DIR.mkdir(parents=True)

    env = os.environ.copy()
    env["PYTHONPATH"] = str(E2E_DIR) + os.pathsep + env.get("PYTHONPATH", "")

    dist_dir = TMP_DIR / "dist"

    result = subprocess.run(
        [
            "uv",
            "run",
            "--project",
            str(PROJECT_ROOT),
            "python",
            "-m",
            "webcompy",
            "generate",
            "--dist",
            str(dist_dir),
        ],
        cwd=str(E2E_DIR),
        env=env,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, f"Generate failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
    assert dist_dir.exists(), f"Dist dir not created: {dist_dir}"

    wheel_dir = dist_dir / "_webcompy-app-package"
    assert wheel_dir.exists(), f"Wheel dir not created: {wheel_dir}"

    wheel_files = list(wheel_dir.glob("*.whl"))
    assert len(wheel_files) >= 1, f"Expected at least 1 wheel, found {len(wheel_files)}: {wheel_files}"

    yield dist_dir, wheel_files[0], app_dir.name

    if TMP_DIR.exists():
        shutil.rmtree(TMP_DIR)


@pytest.fixture(scope="session")
def split_static_site():
    app_dir = E2E_DIR / "my_app"

    split_tmp = TMP_DIR / "e2e-split-static"
    if split_tmp.exists():
        shutil.rmtree(split_tmp)
    split_tmp.mkdir(parents=True)

    env = os.environ.copy()
    env["PYTHONPATH"] = str(E2E_DIR) + os.pathsep + env.get("PYTHONPATH", "")

    dist_dir = split_tmp / "dist"

    result = subprocess.run(
        [
            "uv",
            "run",
            "--project",
            str(PROJECT_ROOT),
            "python",
            "-m",
            "webcompy",
            "generate",
            "--dist",
            str(dist_dir),
            "--wheel-mode",
            "split",
        ],
        cwd=str(E2E_DIR),
        env=env,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, f"Split generate failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
    assert dist_dir.exists(), f"Dist dir not created: {dist_dir}"

    wheel_dir = dist_dir / "_webcompy-app-package"
    assert wheel_dir.exists(), f"Wheel dir not created: {wheel_dir}"

    wheel_files = list(wheel_dir.glob("*.whl"))
    assert len(wheel_files) == 2, (
        f"Expected exactly 2 wheels in split mode, found {len(wheel_files)}: {[f.name for f in wheel_files]}"
    )

    app_wheel = next(
        (f for f in wheel_files if f.name.startswith(app_dir.name) and "0+sha." in f.name),
        wheel_files[0],
    )
    framework_wheel = next(
        (f for f in wheel_files if f.name.startswith("webcompy-") and "0+sha." in f.name),
        None,
    )
    assert framework_wheel is not None, f"No content-hash framework wheel found in {[f.name for f in wheel_files]}"

    yield dist_dir, app_wheel, framework_wheel, app_dir.name, wheel_files

    if split_tmp.exists():
        shutil.rmtree(split_tmp)


@pytest.fixture(scope="session")
def static_server(static_site):
    dist_dir, _, _ = static_site

    handler_class = partial(_QuietHandler, directory=str(dist_dir))
    server = HTTPServer(("127.0.0.1", 0), handler_class)
    port = server.server_address[1]

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    for _ in range(30):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=2)
            break
        except Exception:
            time.sleep(0.5)

    yield f"http://127.0.0.1:{port}/"

    server.shutdown()


@pytest.fixture
def server_url(serving_mode, prod_server, static_server):
    if serving_mode == "prod":
        return BASE_URL
    return static_server


@pytest.fixture
def console_messages(page: Page):
    messages: list[ConsoleMessage] = []
    _collect_console_messages(page, messages)
    yield messages


@pytest.fixture
def console_errors(console_messages: list[ConsoleMessage]):
    yield [m.text for m in console_messages if m.type == "error"]


@pytest.fixture
def app_page(page: Page, server_url, console_messages):
    page.goto(server_url)
    _wait_for_pyscript_init(page, console_messages)
    return page


@pytest.fixture
def page_on(page: Page, server_url, console_messages) -> Callable[[str], Page]:
    def _navigate(path: str) -> Page:
        page.goto(f"{server_url}{path.lstrip('/')}")
        _wait_for_pyscript_init(page, console_messages)
        return page

    return _navigate


def _write_console_log(request, console_messages_list: list[ConsoleMessage]):
    if not CONSOLE_LOG_DIR:
        return
    level = _CONSOLE_LEVEL_ORDER[CONSOLE_FILE_LEVEL]
    filtered = [m for m in console_messages_list if _CONSOLE_LEVEL_ORDER.get(m.type, 0) <= level]
    if not filtered:
        return
    log_dir = pathlib.Path(CONSOLE_LOG_DIR)
    log_dir.mkdir(parents=True, exist_ok=True)
    test_name = request.node.name.replace("/", "_").replace("::", "__").replace(" ", "_")
    log_path = log_dir / f"console-{test_name}.log"
    with log_path.open("w") as f:
        for m in filtered:
            f.write(m.format() + "\n")


@pytest.fixture
def assert_no_console_errors(console_messages: list[ConsoleMessage], request):
    yield
    _write_console_log(request, console_messages)
    _check_asset_errors(console_messages)
    python_errors = [
        m for m in console_messages if m.type == "error" and any(p in m.text for p in _PYTHON_TRACEBACK_PATTERNS)
    ]
    assert not python_errors, f"Python errors detected in browser console ({len(python_errors)}):\n" + "\n---\n".join(
        m.format() for m in python_errors
    )


@pytest.fixture(autouse=True)
def _check_console_errors_after_test(request):
    console_messages = request.getfixturevalue("console_messages") if "page" in request.fixturenames else None
    yield
    if console_messages is not None:
        _write_console_log(request, console_messages)
        _check_asset_errors(console_messages)
        python_errors = [
            m for m in console_messages if m.type == "error" and any(p in m.text for p in _PYTHON_TRACEBACK_PATTERNS)
        ]
        if python_errors:
            pytest.fail(
                f"Python errors detected in browser console ({len(python_errors)}):\n"
                + "\n---\n".join(m.format() for m in python_errors[:5])
            )
