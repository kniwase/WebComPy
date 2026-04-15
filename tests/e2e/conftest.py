from __future__ import annotations

import os
import subprocess
import time
import urllib.request
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from playwright.sync_api import Page

PROJECT_ROOT = Path(__file__).parent.parent.parent
E2E_DIR = Path(__file__).parent
BASE_URL = "http://localhost:8088/"
PORT = 8088
PYSCRIPT_INIT_TIMEOUT = 120_000
SERVER_LOG = Path(__file__).parent / ".e2e-server.log"


def pytest_configure(config):
    config.addinivalue_line("markers", "e2e: End-to-end tests requiring a browser and dev server")


@pytest.fixture(scope="session")
def dev_server():
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
            "--dev",
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
                pytest.fail(f"Dev server exited prematurely (code {proc.returncode}):\n{log_content}")
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
        pytest.fail(f"Dev server did not start within 120 seconds:\n{log_content}")

    yield proc

    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=5)
    finally:
        log_file.close()


@pytest.fixture
def app_page(page: Page, dev_server):
    page.goto(BASE_URL)
    page.wait_for_selector("#webcompy-loading", state="hidden", timeout=PYSCRIPT_INIT_TIMEOUT)
    return page


@pytest.fixture
def page_on(page: Page, dev_server) -> Callable[[str], Page]:
    def _navigate(path: str) -> Page:
        page.goto(f"{BASE_URL}{path.lstrip('/')}")
        page.wait_for_selector("#webcompy-loading", state="hidden", timeout=PYSCRIPT_INIT_TIMEOUT)
        return page

    return _navigate
