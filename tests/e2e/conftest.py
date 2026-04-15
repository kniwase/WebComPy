from __future__ import annotations

import subprocess
import time
import urllib.request
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from playwright.sync_api import Page

E2E_DIR = Path(__file__).parent
BASE_URL = "http://localhost:8088/WebComPy/"
PORT = 8088
PYSSCRIPT_INIT_TIMEOUT = 120_000


def pytest_configure(config):
    config.addinivalue_line("markers", "e2e: End-to-end tests requiring a browser and dev server")


@pytest.fixture(scope="session")
def dev_server():
    proc = subprocess.Popen(
        [
            "uv",
            "run",
            "python",
            "-m",
            "webcompy",
            "start",
            "--dev",
            "--port",
            str(PORT),
        ],
        cwd=str(E2E_DIR),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    for _ in range(120):
        try:
            urllib.request.urlopen(BASE_URL, timeout=5)
            break
        except Exception:
            if proc.poll() is not None:
                stdout = proc.stdout.read().decode()
                stderr = proc.stderr.read().decode()
                pytest.fail(f"Dev server exited prematurely:\nstdout: {stdout}\nstderr: {stderr}")
            time.sleep(1)
    else:
        proc.terminate()
        pytest.fail("Dev server did not start within 120 seconds")

    yield proc

    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=5)


@pytest.fixture
def app_page(page: Page, dev_server):
    page.goto(BASE_URL)
    page.wait_for_selector("#webcompy-loading", state="hidden", timeout=PYSSCRIPT_INIT_TIMEOUT)
    return page


@pytest.fixture
def page_on(page: Page, dev_server) -> Callable[[str], Page]:
    def _navigate(path: str) -> Page:
        page.goto(f"{BASE_URL}{path.lstrip('/')}")
        page.wait_for_selector("#webcompy-loading", state="hidden", timeout=PYSSCRIPT_INIT_TIMEOUT)
        return page

    return _navigate
