from __future__ import annotations

import contextlib
import os
import pathlib
import shutil
import socket
import subprocess
import threading
import time
import urllib.request
from functools import partial
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse

import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.e2e

PROJECT_ROOT = pathlib.Path(__file__).parent.parent.parent
E2E_DIR = pathlib.Path(__file__).parent
TMP_DIR = pathlib.Path(os.environ.get("E2E_TMP_DIR", str(PROJECT_ROOT / ".tmp" / "e2e-pwa")))
SW_TIMEOUT_MS = 60_000

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
_OFFLINE_CONSOLE_NOISE = ("ERR_INTERNET_DISCONNECTED", "ERR_FAILED")


@pytest.fixture(autouse=True)
def _check_console_errors_after_test(request):
    """Console gate for this module that tolerates deliberate offline noise.

    The offline PWA scenarios produce net::ERR_INTERNET_DISCONNECTED console
    errors by design; every other error keeps the shared conftest semantics.
    """
    console_messages = request.getfixturevalue("console_messages") if "page" in request.fixturenames else None
    yield
    if console_messages is None:
        return
    python_errors = [
        m for m in console_messages if m.type == "error" and any(p in m.text for p in _PYTHON_TRACEBACK_PATTERNS)
    ]
    assert not python_errors, "Python errors in browser console"
    if request.node.get_closest_marker("pwa_transient_asset_errors") is not None:
        return
    asset_errors = [
        m
        for m in console_messages
        if m.type == "error"
        and any(p in m.text for p in _ASSET_ERROR_PATTERNS)
        and not any(noise in m.text for noise in _OFFLINE_CONSOLE_NOISE)
    ]
    if asset_errors:
        pytest.fail("Asset loading errors: " + " | ".join(m.text for m in asset_errors[:5]))


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


def _free_port() -> int:
    s = socket.socket()
    s.bind(("", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _base_env(**extra: str) -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(E2E_DIR) + os.pathsep + env.get("PYTHONPATH", "")
    env.update(extra)
    return env


def _wait_url(url: str, proc: subprocess.Popen, log_file, timeout_s: int = 180) -> None:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        try:
            urllib.request.urlopen(url, timeout=5)
            return
        except Exception:
            if proc.poll() is not None:
                pytest.fail(f"Server exited prematurely:\n{log_file.name}")
            time.sleep(1)
    pytest.fail(f"Server did not start within {timeout_s}s")


def _start_server(config: str, port: int, env_extra: dict[str, str]):
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    log_file = TMP_DIR / f"pwa-server-{port}.log"
    handle = log_file.open("w")
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
            config,
            "--port",
            str(port),
        ],
        cwd=str(E2E_DIR),
        stdout=handle,
        stderr=subprocess.STDOUT,
        env=_base_env(**env_extra),
    )
    return proc, handle


def _generate(dist_dir: pathlib.Path, env_extra: dict[str, str] | None = None) -> None:
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
            "--config",
            "pwa_config",
            "--dist",
            str(dist_dir),
        ],
        cwd=str(E2E_DIR),
        capture_output=True,
        text=True,
        env=_base_env(**(env_extra or {})),
    )
    assert result.returncode == 0, f"Generate failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"


def _serve_dist(dist_dir: pathlib.Path):
    server = HTTPServer(("127.0.0.1", 0), partial(_QuietHandler, directory=str(dist_dir)))
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{port}/"
    _wait_local(url)
    return server, url


def _wait_local(url: str, timeout_s: int = 60) -> None:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        try:
            urllib.request.urlopen(url, timeout=2)
            return
        except Exception:
            time.sleep(0.3)
    pytest.fail(f"Static server did not start: {url}")


@pytest.fixture(scope="module")
def pwa_prod_server():
    port = _free_port()
    proc, handle = _start_server("pwa_config", port, {})
    base = f"http://localhost:{port}/"
    _wait_url(base + "manifest.webmanifest", proc, handle)
    yield base
    proc.terminate()
    try:
        proc.wait(timeout=10)
    finally:
        handle.close()


@pytest.fixture(scope="module")
def pwa_static_server():
    dist_dir = TMP_DIR / "static-dist"
    if dist_dir.exists():
        shutil.rmtree(dist_dir)
    dist_dir.mkdir(parents=True)
    _generate(dist_dir)
    server, url = _serve_dist(dist_dir)
    yield url
    server.shutdown()


@pytest.fixture
def pwa_base(serving_mode, request):
    if serving_mode == "prod":
        return request.getfixturevalue("pwa_prod_server")
    return request.getfixturevalue("pwa_static_server")


def _page_setup(page) -> None:
    page.set_default_timeout(SW_TIMEOUT_MS)


def _goto_and_wait_worker(page, url: str) -> None:
    _page_setup(page)
    page.goto(url, wait_until="domcontentloaded")
    page.wait_for_function(
        "() => navigator.serviceWorker.getRegistrations().then(rs => rs.length > 0)",
        timeout=SW_TIMEOUT_MS,
    )
    page.evaluate("() => navigator.serviceWorker.ready.then(() => true)")


def _worker_scope(page) -> str:
    return page.evaluate(
        "async () => { const r = await navigator.serviceWorker.getRegistration(); return r ? r.scope : null; }"
    )


def _cache_names(page) -> list[str]:
    return page.evaluate("() => caches.keys()")


class TestManifestDelivery:
    def test_manifest_link_present(self, pwa_base, page, console_messages):
        _page_setup(page)
        page.goto(pwa_base, wait_until="domcontentloaded")
        expected = urlparse(pwa_base).path + "manifest.webmanifest"
        expect(page.locator("link[rel='manifest']")).to_have_attribute("href", expected)

    def test_manifest_is_fetchable_and_resolves_base_url(self, pwa_base, page, console_messages):
        _page_setup(page)
        response = page.request.get(pwa_base + "manifest.webmanifest")
        assert response.status == 200
        body = response.json()
        assert body["name"] == "PWA E2E App"
        assert body["start_url"] == urlparse(pwa_base).path
        assert body["scope"] == urlparse(pwa_base).path

    def test_sw_js_is_served_with_embedded_config(self, pwa_base, page, console_messages):
        _page_setup(page)
        response = page.request.get(pwa_base + "sw.js")
        assert response.status == 200
        text = response.text()
        assert '"pattern":"/about/"' in text
        assert '"fallback":"pwa_offline.html"' in text
        assert '"1.0.0-' in text


class TestWorkerRegistration:
    def test_worker_registers_at_base_scope(self, pwa_base, page, console_messages):
        _goto_and_wait_worker(page, pwa_base)
        assert _worker_scope(page) == pwa_base


class TestOfflineBehavior:
    def test_offline_unknown_navigation_serves_custom_fallback(self, pwa_base, page, console_messages):
        _goto_and_wait_worker(page, pwa_base)
        page.context.set_offline(True)
        response = page.goto(pwa_base + "never-generated-route/", wait_until="domcontentloaded")
        assert response.status == 200
        assert "Custom Offline Page Active" in response.text()

    def test_offline_precached_page_served_via_clean_url(self, serving_mode, pwa_base, page, console_messages):
        if serving_mode != "static":
            pytest.skip("precache enumeration is an SSG-output scenario")
        _goto_and_wait_worker(page, pwa_base)
        page.context.set_offline(True)
        page.goto(pwa_base + "about/", wait_until="domcontentloaded")
        assert page.evaluate("() => navigator.serviceWorker.controller !== null")
        expect(page.locator("[data-testid='about-page'] h1")).to_have_text("PWA About Page")

    def test_offline_precached_page_served_via_index_retry(self, serving_mode, pwa_base, page, console_messages):
        if serving_mode != "static":
            pytest.skip("precache enumeration is an SSG-output scenario")
        _goto_and_wait_worker(page, pwa_base)
        page.context.set_offline(True)
        page.goto(pwa_base + "about", wait_until="domcontentloaded")
        expect(page.locator("[data-testid='about-page'] h1")).to_have_text("PWA About Page")


class TestPrefixedDeployment:
    @pytest.mark.pwa_transient_asset_errors
    def test_registration_scope_follows_base_url_prefix(self, serving_mode, page, console_messages):
        if serving_mode != "prod":
            pytest.skip("prefixed serving is exercised against the prod server")
        port = _free_port()
        proc, handle = _start_server("pwa_config", port, {"PWA_BASE_URL": "/pwa/"})
        base = f"http://localhost:{port}/pwa/"
        try:
            _wait_url(base + "manifest.webmanifest", proc, handle)
            _goto_and_wait_worker(page, base)
            assert _worker_scope(page) == base
            response = page.request.get(base + "sw.js")
            assert response.status == 200
            expected = urlparse(base).path + "manifest.webmanifest"
            expect(page.locator("link[rel='manifest']")).to_have_attribute("href", expected)
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            finally:
                handle.close()


class TestBuildRotation:
    @pytest.mark.pwa_transient_asset_errors
    def test_new_build_activation_cleans_old_caches(self, serving_mode, page, console_messages):
        if serving_mode != "static":
            pytest.skip("cache rotation is verified against generated output")
        dist_dir = TMP_DIR / "rotation-dist"
        if dist_dir.exists():
            shutil.rmtree(dist_dir)
        dist_dir.mkdir(parents=True)
        _generate(dist_dir, {"PWA_VERSION": "1.0.0"})
        server, url = _serve_dist(dist_dir)
        try:
            _goto_and_wait_worker(page, url)
            first = [n for n in _cache_names(page) if n.startswith("webcompy-pwa-")]
            assert any("1.0.0" in n for n in first), f"first-build caches: {first}"

            _generate(dist_dir, {"PWA_VERSION": "2.0.0"})

            deadline = time.monotonic() + 120
            current: list[str] = []
            while time.monotonic() < deadline:
                page.evaluate(
                    "async () => { const r = await navigator.serviceWorker.getRegistration(); if (r) await r.update(); }"
                )
                with contextlib.suppress(Exception):
                    page.goto(url, wait_until="domcontentloaded")
                time.sleep(1.0)
                current = [n for n in _cache_names(page) if n.startswith("webcompy-pwa-")]
                if current and all("2.0.0" in n for n in current) and not any("1.0.0" in n for n in current):
                    break
            else:
                pytest.fail(f"old caches were not cleaned; current: {current}")
            expect(page.locator("[data-testid='home-page'] h1")).to_have_text("PWA Home Page")
        finally:
            server.shutdown()
