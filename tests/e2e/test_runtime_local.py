from __future__ import annotations

import os
import pathlib
import shutil
import subprocess
import threading
import time
import urllib.request
from functools import partial
from http.server import HTTPServer, SimpleHTTPRequestHandler

import pytest

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(os.environ.get("CI") == "true", reason="Requires external CDN access"),
]

PROJECT_ROOT = pathlib.Path(__file__).parent.parent.parent
E2E_DIR = pathlib.Path(__file__).parent
PORT = 8089
TMP_DIR = PROJECT_ROOT / ".tmp" / "e2e-runtime-local"


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


@pytest.fixture(scope="module")
def runtime_local_server():
    env = os.environ.copy()
    env["PYTHONPATH"] = str(E2E_DIR) + os.pathsep + env.get("PYTHONPATH", "")

    log_path = TMP_DIR / "server.log"
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    log_file = log_path.open("w")

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
            "--runtime-serving",
            "local",
        ],
        cwd=str(E2E_DIR),
        stdout=log_file,
        stderr=subprocess.STDOUT,
        env=env,
    )

    base_url = f"http://localhost:{PORT}/"
    for _ in range(120):
        try:
            urllib.request.urlopen(base_url, timeout=5)
            break
        except Exception:
            if proc.poll() is not None:
                log_file.close()
                log_content = log_path.read_text()
                pytest.fail(f"Runtime-local server exited prematurely (code {proc.returncode}):\n{log_content}")
            time.sleep(1)
    else:
        log_file.close()
        log_content = log_path.read_text()
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)
        pytest.fail(f"Runtime-local server did not start within 120 seconds:\n{log_content}")

    yield base_url

    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=5)
    finally:
        log_file.close()


@pytest.fixture(scope="module")
def runtime_local_static_site():
    if TMP_DIR.exists():
        shutil.rmtree(TMP_DIR)
    TMP_DIR.mkdir(parents=True, exist_ok=True)

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
            "--runtime-serving",
            "local",
        ],
        cwd=str(E2E_DIR),
        env=env,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, f"Generate failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
    yield dist_dir

    if TMP_DIR.exists():
        shutil.rmtree(TMP_DIR)


@pytest.fixture(scope="module")
def runtime_local_static_server(runtime_local_static_site):
    dist_dir = runtime_local_static_site

    handler_class = partial(_QuietHandler, directory=str(dist_dir))
    server = HTTPServer(("127.0.0.1", 0), handler_class)
    port = server.server_address[1]

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    base_url = f"http://127.0.0.1:{port}/"
    for _ in range(30):
        try:
            urllib.request.urlopen(base_url, timeout=2)
            break
        except Exception:
            time.sleep(0.5)

    yield base_url

    server.shutdown()


def test_runtime_local_html_uses_local_assets(runtime_local_server, page):
    page.goto(runtime_local_server)
    page.wait_for_selector("#webcompy-loading", state="hidden", timeout=120_000)
    page.wait_for_selector("#webcompy-app:not([hidden])", timeout=120_000)

    script_src = page.evaluate("""() => {
        const s = document.querySelector('script[src*="core.js"]');
        return s ? s.getAttribute('src') : null;
    }""")
    assert script_src is not None
    assert "/_webcompy-assets/core.js" in script_src


def test_runtime_local_no_cdn_requests(runtime_local_server, page):
    cdn_requests: list[str] = []

    def on_request(request):
        url = request.url
        if "pyscript.net" in url or "cdn.jsdelivr.net/pyodide" in url:
            cdn_requests.append(url)

    page.on("request", on_request)
    page.goto(runtime_local_server)
    page.wait_for_selector("#webcompy-loading", state="hidden", timeout=120_000)
    page.wait_for_selector("#webcompy-app:not([hidden])", timeout=120_000)

    assert cdn_requests == [], f"CDN requests detected: {cdn_requests}"


def test_runtime_local_static_no_cdn_urls(runtime_local_static_site):
    dist_dir = runtime_local_static_site
    html_content = (dist_dir / "index.html").read_text(encoding="utf-8")
    assert "pyscript.net" not in html_content
    assert "cdn.jsdelivr.net/pyodide" not in html_content


def test_runtime_local_static_assets_exist(runtime_local_static_site):
    dist_dir = runtime_local_static_site
    assert (dist_dir / "_webcompy-assets" / "core.js").exists()
    assert (dist_dir / "_webcompy-assets" / "core.css").exists()
    assert (dist_dir / "_webcompy-assets" / "pyodide" / "pyodide.mjs").exists()
    assert (dist_dir / "_webcompy-assets" / "pyodide" / "pyodide-lock.json").exists()
