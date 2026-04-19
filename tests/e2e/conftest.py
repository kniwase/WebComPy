from __future__ import annotations

import os
import pathlib
import shutil
import subprocess
import threading
import time
import urllib.request
from collections.abc import Callable
from functools import partial
from http.server import HTTPServer, SimpleHTTPRequestHandler
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from playwright.sync_api import Page

PROJECT_ROOT = pathlib.Path(__file__).parent.parent.parent
E2E_DIR = pathlib.Path(__file__).parent
BASE_URL = "http://localhost:8088/"
PORT = 8088
PYSCRIPT_INIT_TIMEOUT = 120_000
SERVER_LOG = pathlib.Path(__file__).parent / ".e2e-server.log"
TMP_DIR = pathlib.Path(__file__).parent.parent.parent / ".tmp" / "e2e-static"

_PYTHON_TRACEBACK_PATTERNS = (
    "Traceback (most recent call last):",
    "micropip._vendored.",
    "pyodide.",
)


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


def pytest_configure(config):
    config.addinivalue_line("markers", "e2e: End-to-end tests requiring a browser and server")


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
    assert len(wheel_files) == 1, f"Expected 1 wheel, found {len(wheel_files)}: {wheel_files}"

    yield dist_dir, wheel_files[0], app_dir.name

    if TMP_DIR.exists():
        shutil.rmtree(TMP_DIR)


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


@pytest.fixture(params=["prod", "static"], ids=["prod", "static"])
def serving_mode(request):
    return request.param


@pytest.fixture
def server_url(serving_mode, prod_server, static_server):
    if serving_mode == "prod":
        return BASE_URL
    return static_server


@pytest.fixture
def app_page(page: Page, server_url):
    page.goto(server_url)
    page.wait_for_selector("#webcompy-loading", state="hidden", timeout=PYSCRIPT_INIT_TIMEOUT)
    page.wait_for_selector("#webcompy-app:not([hidden])", timeout=PYSCRIPT_INIT_TIMEOUT)
    return page


@pytest.fixture
def page_on(page: Page, server_url) -> Callable[[str], Page]:
    def _navigate(path: str) -> Page:
        page.goto(f"{server_url}{path.lstrip('/')}")
        page.wait_for_selector("#webcompy-loading", state="hidden", timeout=PYSCRIPT_INIT_TIMEOUT)
        page.wait_for_selector("#webcompy-app:not([hidden])", timeout=PYSCRIPT_INIT_TIMEOUT)
        return page

    return _navigate


@pytest.fixture
def console_errors(page: Page):
    errors: list[str] = []

    def on_console_msg(msg):
        if msg.type == "error":
            errors.append(msg.text)

    page.on("console", on_console_msg)
    yield errors


@pytest.fixture
def assert_no_python_errors(console_errors: list[str]):
    yield
    python_errors = [err for err in console_errors if any(pattern in err for pattern in _PYTHON_TRACEBACK_PATTERNS)]
    assert not python_errors, f"Python errors detected in browser console ({len(python_errors)}):\n" + "\n---\n".join(
        python_errors
    )
