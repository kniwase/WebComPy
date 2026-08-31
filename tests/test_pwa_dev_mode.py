from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from webcompy.app import WebComPyApp, WebComPyAppConfig
from webcompy.components._generator import define_component
from webcompy_cli.config import ManifestConfig, PWAConfig, WebComPyBuildConfig
from webcompy_server import configure_server_context


@define_component()
def PwaDevRoot(context):
    from webcompy.elements import html

    return html.DIV({}, "dev")


def _make_build_config(tmp_path: Path, pwa: PWAConfig) -> WebComPyBuildConfig:
    pkg = tmp_path / "app"
    pkg.mkdir()
    mod_path = pkg / "_app_mod.py"
    mod_path.write_text("app = None\n", encoding="utf-8")
    import importlib.util

    spec = importlib.util.spec_from_file_location("_ephemeral_pwa_dev", mod_path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return WebComPyBuildConfig(app_module=mod, pwa=pwa)


def _create_serving(app, build_config, mode: str):
    from webcompy_cli._build import BuildArtifacts
    from webcompy_cli._server import create_asgi_app

    artifacts = BuildArtifacts(
        app_version="1.0.0",
        wheel_filename="app.whl",
        app_package_files={"app.whl": (b"x", "application/zip")},
        dev_mode=mode == "dev",
    )
    with (
        patch("webcompy_cli._server.resolve_build_artifacts", return_value=artifacts),
        patch("webcompy_cli._server.get_static_files", return_value=()),
    ):
        configure_server_context(app)
        return create_asgi_app(app, build_config, mode=mode)


def _app() -> WebComPyApp:
    return WebComPyApp(root_component=PwaDevRoot, config=WebComPyAppConfig())


class TestDevModeDisabledByDefault:
    @pytest.mark.asyncio
    async def test_dev_serves_no_worker_or_manifest(self, tmp_path):
        import httpx

        serving = _create_serving(_app(), _make_build_config(tmp_path, PWAConfig()), mode="dev")
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=serving.asgi), base_url="http://test") as client:
            worker = await client.get("/sw.js")
            manifest = await client.get("/manifest.webmanifest")
        assert worker.status_code == 404
        assert manifest.status_code == 404

    @pytest.mark.asyncio
    async def test_dev_html_has_no_pwa_injection(self, tmp_path):
        import httpx

        serving = _create_serving(_app(), _make_build_config(tmp_path, PWAConfig()), mode="dev")
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=serving.asgi), base_url="http://test") as client:
            page = await client.get("/")
        assert page.status_code == 200
        assert 'rel="manifest"' not in page.text
        assert "serviceWorker" not in page.text


class TestDevModeExplicitEnablement:
    @pytest.mark.asyncio
    async def test_dev_with_pwa_enabled_serves_and_injects(self, tmp_path):
        import httpx

        pwa = PWAConfig(enabled=True, manifest=ManifestConfig(name="Dev PWA"))
        serving = _create_serving(_app(), _make_build_config(tmp_path, pwa), mode="dev")
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=serving.asgi), base_url="http://test") as client:
            worker = await client.get("/sw.js")
            manifest = await client.get("/manifest.webmanifest")
            page = await client.get("/")
        assert worker.status_code == 200
        assert manifest.status_code == 200
        assert 'rel="manifest"' in page.text
        assert "navigator.serviceWorker.register" in page.text
