import os
import pathlib
import re
import shutil
import subprocess
import threading
import time
import urllib.request
from http.server import HTTPServer, SimpleHTTPRequestHandler

import pytest

from webcompy.cli._wheel_builder import get_wheel_filename

PROJECT_ROOT = pathlib.Path(__file__).parent.parent.parent
E2E_DIR = pathlib.Path(__file__).parent
TMP_DIR = pathlib.Path(__file__).parent.parent.parent / ".tmp" / "e2e-static"

PYSCRIPT_INIT_TIMEOUT = 120_000


class _QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass


def _extract_version_from_wheel_name(name: str) -> str | None:
    m = re.match(r".+?-(\d+\.\d+\.\d+)-py3-none-any\.whl$", name)
    return m.group(1) if m else None


@pytest.fixture(scope="session")
def static_site():
    app_dir = E2E_DIR / "app"

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
    _dist_dir, _, _ = static_site

    server = HTTPServer(("127.0.0.1", 0), _QuietHandler)
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
def static_page(page, static_server):
    page.goto(static_server)
    page.wait_for_selector("#webcompy-loading", state="hidden", timeout=PYSCRIPT_INIT_TIMEOUT)
    return page


@pytest.mark.e2e
class TestStaticSiteWheelFilename:
    def test_wheel_filename_matches_html_url(self, static_site):
        dist_dir, wheel_file, app_name = static_site

        version = _extract_version_from_wheel_name(wheel_file.name)
        assert version is not None, f"Could not extract version from wheel filename: {wheel_file.name}"

        expected_filename = get_wheel_filename(app_name, version)
        assert wheel_file.name == expected_filename, (
            f"Wheel filename {wheel_file.name!r} does not match expected {expected_filename!r}"
        )

        html_path = dist_dir / "index.html"
        assert html_path.exists()
        html_content = html_path.read_text(encoding="utf-8")
        assert f"_webcompy-app-package/{wheel_file.name}" in html_content, (
            f"Wheel filename {wheel_file.name!r} not found in HTML. "
            f"Expected URL containing '_webcompy-app-package/{wheel_file.name}'"
        )

    def test_wheel_is_valid_zip(self, static_site):
        import zipfile

        _, wheel_file, _ = static_site
        assert zipfile.is_zipfile(wheel_file), f"Wheel file is not a valid zip: {wheel_file}"

    def test_app_loads_in_browser(self, static_page):
        from playwright.sync_api import expect

        expect(static_page.locator("#webcompy-app")).to_be_visible()
