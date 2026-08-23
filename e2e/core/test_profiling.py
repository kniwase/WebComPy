import os
import socket
import subprocess
import time
import urllib.request
from pathlib import Path

import pytest

pytestmark = pytest.mark.e2e

PROJECT_ROOT = Path(__file__).parent.parent.parent
E2E_DIR = Path(__file__).parent


def _free_port():
    s = socket.socket()
    s.bind(("", 0))
    port = s.getsockname()[1]
    s.close()
    return port


@pytest.fixture
def profile_server(serving_mode):
    if serving_mode == "static":
        pytest.skip("Profiling summary E2E targets the live prod server only")
    port = _free_port()
    env = os.environ.copy()
    env["PYTHONPATH"] = str(E2E_DIR) + os.pathsep + env.get("PYTHONPATH", "")
    tmp_dir = Path(os.environ.get("E2E_TMP_DIR", str(PROJECT_ROOT / ".tmp")))
    tmp_dir.mkdir(parents=True, exist_ok=True)
    log_file = (tmp_dir / f"profile-{port}.log").open("w")
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
            "--config",
            "profile_config",
            "--port",
            str(port),
        ],
        cwd=str(E2E_DIR),
        stdout=log_file,
        stderr=subprocess.STDOUT,
        env=env,
    )
    base_url = f"http://localhost:{port}/"
    for _ in range(120):
        try:
            urllib.request.urlopen(base_url, timeout=5)
            break
        except Exception:
            if proc.poll() is not None:
                log_file.close()
                pytest.fail(f"Profile server exited prematurely (code {proc.returncode})")
            time.sleep(1)
    else:
        proc.terminate()
        proc.wait(timeout=10)
        log_file.close()
        pytest.fail("Profile server did not start within 120 seconds")

    yield base_url

    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
    log_file.close()


def _wait_for_boot(page, timeout_ms=120_000):
    page.wait_for_selector("#webcompy-loading", state="hidden", timeout=timeout_ms)
    page.wait_for_selector("#webcompy-app:not([hidden])", timeout=10_000)


def _wait_for_profile_summary(page, messages, timeout_s=15.0):
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        for text in messages:
            if "[WebComPy Profile]" in text:
                return text
        page.wait_for_timeout(200)
    pytest.fail("Profile summary was not printed to the browser console:\n" + "\n---\n".join(messages[-10:]))


def test_profile_summary_printed_in_browser(browser, profile_server):
    messages = []
    page = browser.new_page()
    page.on("console", lambda msg: messages.append(msg.text))
    try:
        page.goto(profile_server)

        _wait_for_boot(page)
        summary = _wait_for_profile_summary(page, messages)

        assert "pyscript_ready → imports_done" in summary
        assert "custom_elements_defined" in summary
        assert "lazy_preload_start → lazy_preloaded" in summary
        assert any(line.strip().startswith("Total:") for line in summary.splitlines())
    finally:
        page.close()
