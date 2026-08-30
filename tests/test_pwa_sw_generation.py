from __future__ import annotations

import json
import re
from pathlib import Path
from unittest.mock import patch

import pytest

from webcompy_cli._pwa import (
    SW_FILENAME,
    build_precache_entries,
    generate_sw,
    precache_entries_for_artifacts,
    runtime_entry_urls,
)
from webcompy_cli.config import ManifestConfig, PWAConfig, RuntimeCachingRule


def _pwa(**kwargs) -> PWAConfig:
    kwargs.setdefault("enabled", True)
    kwargs.setdefault("manifest", ManifestConfig(name="A"))
    return PWAConfig(**kwargs)


def _make_dist(tmp_path: Path) -> Path:
    dist = tmp_path / "dist"
    files = {
        "index.html": "<html></html>",
        "documents/foo/index.html": "<html></html>",
        "_webcompy-app-package/app-0+sha.deadbeef-py3-none-any.whl": "wheel",
        "_webcompy-ui/index.css": "css",
        "_webcompy-assets/pyodide/pyodide.mjs": "runtime",
        "_webcompy-assets/pyodide/pyodide.asm.wasm": "runtimewasm",
        "_webcompy-assets/core.js": "core",
        "_webcompy-assets/core.css": "corecss",
        "_webcompy-assets/packages/numpy-1.0-py3-none-any.whl": "wasmwheel",
        "manifest.webmanifest": "{}",
        "sw.js": "old",
    }
    for rel, content in files.items():
        target = dist / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    return dist


RUNTIME_FILES = {
    "pyodide/pyodide.mjs": Path("pyodide.mjs"),
    "pyodide/pyodide.asm.wasm": Path("pyodide.asm.wasm"),
    "core.js": Path("core.js"),
    "core.css": Path("core.css"),
}


class TestBuildPrecacheEntries:
    def test_none_mode_is_empty(self, tmp_path):
        dist = _make_dist(tmp_path)
        assert build_precache_entries(_pwa(precache="none"), dist_dir=dist) == []

    def test_auto_enumerates_pages_and_assets(self, tmp_path):
        dist = _make_dist(tmp_path)
        entries = build_precache_entries(_pwa(), dist_dir=dist)
        assert "index.html" in entries
        assert "./" in entries
        assert "documents/foo/index.html" in entries
        assert "documents/foo/" in entries
        assert "_webcompy-app-package/app-0+sha.deadbeef-py3-none-any.whl" in entries
        assert "_webcompy-ui/index.css" in entries

    def test_pwa_output_files_excluded(self, tmp_path):
        dist = _make_dist(tmp_path)
        entries = build_precache_entries(_pwa(), dist_dir=dist)
        assert "sw.js" not in entries
        assert "manifest.webmanifest" not in entries

    def test_wasm_packages_count_as_assets(self, tmp_path):
        dist = _make_dist(tmp_path)
        entries = build_precache_entries(_pwa(), dist_dir=dist, runtime_asset_files=RUNTIME_FILES)
        assert "_webcompy-assets/packages/numpy-1.0-py3-none-any.whl" in entries

    def test_runtime_excluded_by_default(self, tmp_path):
        dist = _make_dist(tmp_path)
        entries = build_precache_entries(_pwa(), dist_dir=dist, runtime_asset_files=RUNTIME_FILES)
        assert "_webcompy-assets/pyodide/pyodide.mjs" not in entries
        assert "_webcompy-assets/core.js" not in entries
        assert "_webcompy-assets/core.css" not in entries

    def test_runtime_opt_in_local_includes_and_warns(self, tmp_path, capsys):
        dist = _make_dist(tmp_path)
        runtime_files = {rel: dist / "_webcompy-assets" / rel for rel in RUNTIME_FILES}
        entries = build_precache_entries(_pwa(precache_runtime=True), dist_dir=dist, runtime_asset_files=runtime_files)
        assert "_webcompy-assets/pyodide/pyodide.mjs" in entries
        assert "_webcompy-assets/core.js" in entries
        err = capsys.readouterr().err
        assert "precache_runtime enabled" in err
        assert "MB" in err

    def test_runtime_opt_in_cdn_warns_partial_coverage(self, tmp_path, capsys):
        dist = _make_dist(tmp_path)
        urls = runtime_entry_urls("https://cdn.example/pyodide-lock.json")
        entries = build_precache_entries(
            _pwa(precache_runtime=True),
            dist_dir=dist,
            runtime_asset_files=None,
            cdn_runtime_urls=urls,
        )
        assert "https://pyscript.net/releases/2026.3.1/core.js" in entries
        assert "https://cdn.example/pyodide-lock.json" in entries
        err = capsys.readouterr().err
        assert "entry files" in err
        assert "not guaranteed" in err

    def test_no_warning_when_runtime_opt_out(self, tmp_path, capsys):
        dist = _make_dist(tmp_path)
        build_precache_entries(_pwa(), dist_dir=dist, runtime_asset_files=RUNTIME_FILES)
        assert "precache_runtime" not in capsys.readouterr().err

    def test_fallback_path_added(self, tmp_path):
        dist = _make_dist(tmp_path)
        (dist / "offline.html").write_text("<html>off</html>", encoding="utf-8")
        entries = build_precache_entries(_pwa(fallback_path="offline.html"), dist_dir=dist)
        assert "offline.html" in entries

    def test_server_mode_no_pages(self):
        pwa = _pwa(precache_runtime=True)
        urls = runtime_entry_urls(None)
        entries = build_precache_entries(pwa, dist_dir=None, runtime_asset_files=None, cdn_runtime_urls=urls)
        assert all(entry.startswith("https://") for entry in entries)

    def test_entries_are_sorted(self, tmp_path):
        dist = _make_dist(tmp_path)
        entries = build_precache_entries(_pwa(), dist_dir=dist)
        assert entries == sorted(entries)

    def test_runtime_entry_urls_lockfile_optional(self):
        without = runtime_entry_urls(None)
        with_lock = runtime_entry_urls("https://example/lock.json")
        assert with_lock[-1] == "https://example/lock.json"
        assert without == with_lock[:-1]


class TestPrecacheEntriesForArtifacts:
    def _artifacts(self, runtime_asset_files=None, lockfile_url=None):
        from webcompy_cli._build import BuildArtifacts

        return BuildArtifacts(
            app_version="1.2.3",
            wheel_filename="app.whl",
            runtime_asset_files=runtime_asset_files,
            lockfile_url=lockfile_url,
        )

    def test_local_runtime_not_included_without_opt_in(self, tmp_path):
        dist = _make_dist(tmp_path)
        runtime_files = {rel: dist / "_webcompy-assets" / rel for rel in RUNTIME_FILES}
        artifacts = self._artifacts(runtime_asset_files=runtime_files)
        entries = precache_entries_for_artifacts(_pwa(), artifacts, dist_dir=dist)
        assert "_webcompy-assets/pyodide/pyodide.mjs" not in entries

    def test_cdn_urls_only_when_opt_in(self, capsys):
        artifacts = self._artifacts(runtime_asset_files=None, lockfile_url="https://cdn/lock.json")
        plain = precache_entries_for_artifacts(_pwa(), artifacts)
        assert plain == []
        opted = precache_entries_for_artifacts(_pwa(precache_runtime=True), artifacts)
        assert "https://cdn/lock.json" in opted
        assert "not guaranteed" in capsys.readouterr().err


class TestGenerateSW:
    def _sw(self, pwa: PWAConfig | None = None, entries: list[str] | None = None, version: str = "1.2.3") -> str:
        return generate_sw(pwa or _pwa(), version, entries if entries is not None else ["./", "index.html"])

    def test_config_embedded(self):
        pwa = _pwa(
            runtime=[RuntimeCachingRule(pattern="/api/", strategy="network-first", max_entries=10, max_age=60)],
            fallback_path="offline.html",
        )
        sw = self._sw(pwa, ["./", "index.html", "offline.html"])
        assert "__WC_PWA_CONFIG__" not in sw
        assert '"pattern":"/api/"' in sw
        assert '"maxEntries":10' in sw
        assert '"maxAge":60' in sw
        assert '"fallback":"offline.html"' in sw
        assert "You're offline" in sw

    def test_rule_cache_matches_full_url(self):
        sw = self._sw()
        assert sw.count("ignoreSearch") == 1
        assert "cache.match(request, { ignoreSearch" not in sw
        assert "cache.match(request)" in sw

    def test_version_embedded_in_cache_names(self):
        sw = self._sw(version="7.7.7")
        match = re.search(r'"version":"([^"]+)"', sw)
        assert match is not None
        version = match.group(1)
        assert version.startswith("7.7.7-")
        assert re.search(r"-[0-9a-f]{12}$", version)
        assert 'PRECACHE_NAME = PREFIX + "v-" + CONFIG.version' in sw

    def test_config_hash_rotates_with_precache(self):
        def version_of(entries: list[str]) -> str:
            sw = self._sw(entries=entries)
            return re.search(r'"version":"([^"]+)"', sw).group(1)

        a = version_of(["./", "index.html"])
        b = version_of(["./", "index.html", "page/index.html"])
        assert a.split("-")[1] != b.split("-")[1]
        assert a == version_of(["./", "index.html"])

    def test_template_structure(self):
        sw = self._sw()
        assert 'self.addEventListener("install"' in sw
        assert 'self.addEventListener("activate"' in sw
        assert 'self.addEventListener("fetch"' in sw
        assert "skipWaiting" in sw
        assert "clients.claim" in sw
        assert '"/index.html"' in sw
        assert "scopeRelative" in sw
        assert "no-cors" in sw
        assert "X-WebComPy-Offline" in sw

    def test_script_end_sequences_escaped(self):
        sw = self._sw(entries=["</script>"])
        assert "</script>" not in sw


class TestServiceWorkerSourceValidity:
    def test_generated_worker_is_valid_javascript(self, tmp_path):
        import shutil
        import subprocess

        node = shutil.which("node")
        if node is None:
            pytest.skip("node executable not available")
        pwa = _pwa(
            runtime=[
                RuntimeCachingRule(pattern="/api/", strategy="network-first", max_entries=5, max_age=30),
                RuntimeCachingRule(pattern="static/**", strategy="cache-first"),
                RuntimeCachingRule(pattern="*.svg", strategy="stale-while-revalidate"),
            ],
            fallback_path="offline.html",
        )
        sw = generate_sw(pwa, "1.0.0", ["./", "index.html", "offline.html", "https://cdn.example/core.js"])
        target = tmp_path / "sw.js"
        target.write_text(sw, encoding="utf-8")
        result = subprocess.run([node, "--check", str(target)], capture_output=True, text=True)
        assert result.returncode == 0, result.stderr


def _make_app(base_url: str = "/"):
    from webcompy.app import WebComPyApp, WebComPyAppConfig

    return WebComPyApp(root_component=lambda _: None, config=WebComPyAppConfig(base_url=base_url))


def _make_build_config(tmp_path: Path, pwa: PWAConfig) -> object:
    pkg = tmp_path / "app"
    pkg.mkdir()
    mod_path = pkg / "_app_mod.py"
    mod_path.write_text("app = None\n", encoding="utf-8")
    import importlib.util

    spec = importlib.util.spec_from_file_location("_ephemeral_sw", mod_path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    from webcompy_cli.config import WebComPyBuildConfig

    return WebComPyBuildConfig(app_module=mod, pwa=pwa)


def _run_generate(build_config) -> Path:
    import asyncio
    import sys

    app = _make_app()
    build_config.app = app

    async def _trivial_asgi(scope, receive, send):
        if scope["type"] != "http":
            return
        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [(b"content-type", b"text/html")],
            }
        )
        await send({"type": "http.response.body", "body": b"<html></html>"})

    from webcompy_cli._build import BuildArtifacts

    class _FakeServingApp:
        def __init__(self) -> None:
            self.artifacts = BuildArtifacts(
                app_version="test-version",
                wheel_filename="test.whl",
                app_package_files={"test.whl": (b"x", "application/zip")},
            )
            self.asgi = None
            self.html_generator = None
            self.hash_cache: list[str] = []

    serving = _FakeServingApp()
    serving.asgi = _trivial_asgi

    saved_argv = sys.argv
    sys.argv = ["webcompy", "generate"]
    try:
        with (
            patch("webcompy_cli._generate.create_asgi_app", return_value=serving),
            patch("webcompy_cli._generate.discover_config", return_value=build_config),
            patch("webcompy_cli._generate.get_static_files", return_value=()),
            patch("webcompy.ui._styles.get_styles_files", return_value={}, create=True),
        ):
            from webcompy_cli._generate import generate_static_site

            asyncio.run(generate_static_site())
    finally:
        sys.argv = saved_argv
    return build_config.app_package_path / build_config.dist


class TestSSGServiceWorkerEmission:
    def test_sw_written_to_dist_with_precache(self, tmp_path):
        build_config = _make_build_config(tmp_path, _pwa())
        dist = _run_generate(build_config)
        sw_path = dist / SW_FILENAME
        assert sw_path.is_file()
        sw = sw_path.read_text(encoding="utf-8")
        assert '"index.html"' in sw
        assert '"./"' in sw
        assert '"test-version-' in sw

    def test_no_sw_when_disabled(self, tmp_path):
        build_config = _make_build_config(tmp_path, PWAConfig())
        dist = _run_generate(build_config)
        assert not (dist / SW_FILENAME).exists()


def _create_serving(app, build_config):
    from webcompy_cli._build import BuildArtifacts
    from webcompy_cli._server import create_asgi_app

    artifacts = BuildArtifacts(
        app_version="1.2.3",
        wheel_filename="test.whl",
        app_package_files={"test.whl": (b"x", "application/zip")},
    )
    with (
        patch("webcompy_cli._server.resolve_build_artifacts", return_value=artifacts),
        patch("webcompy_cli._server.get_static_files", return_value=()),
    ):
        return create_asgi_app(app, build_config, mode="prod")


class TestServerServiceWorkerServing:
    @pytest.mark.asyncio
    async def test_serves_sw_with_no_cache_header(self, tmp_path):
        import httpx

        app = _make_app()
        build_config = _make_build_config(tmp_path, _pwa())
        serving = _create_serving(app, build_config)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=serving.asgi), base_url="http://test") as client:
            response = await client.get(f"/{SW_FILENAME}")
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("application/javascript")
        assert response.headers["cache-control"] == "no-cache"
        assert '"1.2.3-' in response.text

    @pytest.mark.asyncio
    async def test_serves_sw_under_prefix(self, tmp_path):
        import httpx

        app = _make_app(base_url="/pwa/")
        build_config = _make_build_config(tmp_path, _pwa())
        serving = _create_serving(app, build_config)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=serving.asgi), base_url="http://test") as client:
            response = await client.get("/pwa/sw.js")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_server_precache_empty_without_runtime_opt_in(self, tmp_path):
        import httpx

        app = _make_app()
        build_config = _make_build_config(tmp_path, _pwa())
        serving = _create_serving(app, build_config)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=serving.asgi), base_url="http://test") as client:
            response = await client.get(f"/{SW_FILENAME}")
        config_line = response.text.splitlines()[0]
        config = json.loads(config_line.split(" = ", 1)[1].rstrip(";"))
        assert config["precache"] == []

    @pytest.mark.asyncio
    async def test_disabled_returns_404(self, tmp_path):
        import httpx

        app = _make_app()
        build_config = _make_build_config(tmp_path, PWAConfig())
        serving = _create_serving(app, build_config)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=serving.asgi), base_url="http://test") as client:
            response = await client.get(f"/{SW_FILENAME}")
        assert response.status_code == 404
