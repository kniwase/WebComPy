from __future__ import annotations

import contextlib
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
DOCS_APP_DIR = PROJECT_ROOT / "docs_app"
BASE_URL = "http://localhost:8081/"
PORT = 8081
PYSCRIPT_INIT_TIMEOUT = 300_000
SERVER_LOG = pathlib.Path(__file__).parent / ".e2e-docs-server.log"
TMP_DIR = PROJECT_ROOT / ".tmp" / "e2e-docs-static"

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


def pytest_addoption(parser):
    with contextlib.suppress(ValueError):
        parser.addoption(
            "--serving-mode",
            action="store",
            default=None,
            choices=["prod", "static"],
            help="Run docs E2E tests against a single serving mode (prod or static)",
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


@pytest.fixture(scope="session")
def docs_prod_server():
    env = os.environ.copy()
    env["PYTHONPATH"] = str(PROJECT_ROOT) + os.pathsep + env.get("PYTHONPATH", "")

    log_file = SERVER_LOG.open("w")
    log_file.write(f"=== DEBUG: PYTHONPATH={env.get('PYTHONPATH', '')} ===\n")
    log_file.write(f"=== DEBUG: cwd={PROJECT_ROOT} ===\n")
    log_file.flush()
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
            "--app",
            "docs_app.bootstrap:app",
            "--port",
            str(PORT),
        ],
        cwd=str(PROJECT_ROOT),
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
def docs_static_site():
    if TMP_DIR.exists():
        shutil.rmtree(TMP_DIR)
    TMP_DIR.mkdir(parents=True)

    env = os.environ.copy()
    env["PYTHONPATH"] = str(PROJECT_ROOT) + os.pathsep + env.get("PYTHONPATH", "")

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
            "--app",
            "docs_app.bootstrap:app",
            "--dist",
            str(dist_dir),
        ],
        cwd=str(PROJECT_ROOT),
        env=env,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, f"Generate failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
    assert dist_dir.exists(), f"Dist dir not created: {dist_dir}"

    yield dist_dir

    if TMP_DIR.exists():
        shutil.rmtree(TMP_DIR)


@pytest.fixture(scope="session")
def docs_static_server(docs_static_site):
    dist_dir = docs_static_site

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
def docs_server_url(serving_mode, docs_prod_server, docs_static_server):
    if serving_mode == "prod":
        return BASE_URL
    return docs_static_server


@pytest.fixture
def docs_app_page(page: Page, docs_server_url):
    page.goto(docs_server_url)
    page.wait_for_selector("#webcompy-loading", state="hidden", timeout=PYSCRIPT_INIT_TIMEOUT)
    page.wait_for_selector("#webcompy-app:not([hidden])", timeout=PYSCRIPT_INIT_TIMEOUT)
    return page


@pytest.fixture
def docs_page_on(page: Page, docs_server_url) -> Callable[[str], Page]:
    def _navigate(path: str) -> Page:
        page.goto(f"{docs_server_url}{path.lstrip('/')}")
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
