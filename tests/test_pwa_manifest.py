from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from webcompy_cli._pwa import MANIFEST_FILENAME, serialize_manifest
from webcompy_cli.config import (
    ManifestConfig,
    ManifestIcon,
    PWAConfig,
    WebComPyBuildConfig,
)


class TestSerializeManifest:
    def _pwa(self, manifest: ManifestConfig | None = None) -> PWAConfig:
        return PWAConfig(enabled=True, manifest=manifest or ManifestConfig(name="My App"))

    def test_defaults_resolve_from_base_url(self):
        data = json.loads(serialize_manifest(self._pwa(), "/"))
        assert data["name"] == "My App"
        assert data["start_url"] == "/"
        assert data["scope"] == "/"
        assert data["display"] == "standalone"

    def test_prefixed_base_url(self):
        data = json.loads(serialize_manifest(self._pwa(), "/app/"))
        assert data["start_url"] == "/app/"
        assert data["scope"] == "/app/"

    def test_explicit_start_url_and_scope_win(self):
        manifest = ManifestConfig(name="A", start_url="/entry/", scope="/zone/")
        data = json.loads(serialize_manifest(self._pwa(manifest), "/app/"))
        assert data["start_url"] == "/entry/"
        assert data["scope"] == "/zone/"

    def test_optional_fields_omitted_when_none(self):
        data = json.loads(serialize_manifest(self._pwa(), "/"))
        assert "short_name" not in data
        assert "theme_color" not in data
        assert "background_color" not in data
        assert "icons" not in data

    def test_optional_fields_included_when_set(self):
        manifest = ManifestConfig(
            name="A",
            short_name="A!",
            theme_color="#112233",
            background_color="#ffffff",
        )
        data = json.loads(serialize_manifest(self._pwa(manifest), "/"))
        assert data["short_name"] == "A!"
        assert data["theme_color"] == "#112233"
        assert data["background_color"] == "#ffffff"

    def test_icons_strip_none_values(self):
        manifest = ManifestConfig(
            name="A",
            icons=[
                ManifestIcon(src="icons/a.png", sizes="192x192"),
                ManifestIcon(src="icons/b.png", sizes="512x512", type="image/png", purpose="maskable"),
            ],
        )
        data = json.loads(serialize_manifest(self._pwa(manifest), "/"))
        assert data["icons"] == [
            {"src": "icons/a.png", "sizes": "192x192"},
            {"src": "icons/b.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"},
        ]

    def test_non_ascii_preserved(self):
        raw = serialize_manifest(self._pwa(ManifestConfig(name="日本語アプリ")), "/")
        assert "日本語アプリ" in raw

    def test_requires_manifest(self):
        from webcompy.exception import WebComPyException

        with pytest.raises(WebComPyException, match=r"PWAConfig\.manifest"):
            serialize_manifest(PWAConfig(enabled=True), "/")


def _make_build_config(tmp_path: Path, pwa: PWAConfig) -> WebComPyBuildConfig:
    pkg = tmp_path / "app"
    pkg.mkdir()
    mod_path = pkg / "_app_mod.py"
    mod_path.write_text("app = None\n", encoding="utf-8")
    import importlib.util

    spec = importlib.util.spec_from_file_location("_ephemeral_pwa", mod_path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return WebComPyBuildConfig(app_module=mod, pwa=pwa)


def _make_app(base_url: str = "/"):
    from webcompy.app import WebComPyApp, WebComPyAppConfig

    return WebComPyApp(root_component=lambda _: None, config=WebComPyAppConfig(base_url=base_url))


def _fake_serving():
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

    return _FakeServingApp()


def _run_generate(build_config: WebComPyBuildConfig) -> Path:
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

    serving = _fake_serving()
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


class TestSSGManifestEmission:
    def test_manifest_written_to_dist(self, tmp_path):
        pwa = PWAConfig(enabled=True, manifest=ManifestConfig(name="PWA App"))
        dist_dir = _run_generate(_make_build_config(tmp_path, pwa))
        manifest_path = dist_dir / MANIFEST_FILENAME
        assert manifest_path.is_file()
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert data["name"] == "PWA App"
        assert data["start_url"] == "/"

    def test_no_manifest_when_disabled(self, tmp_path):
        dist_dir = _run_generate(_make_build_config(tmp_path, PWAConfig()))
        assert not (dist_dir / MANIFEST_FILENAME).exists()


def _create_serving(app, build_config, static_files: tuple[str, ...] = ()):
    from webcompy_cli._build import BuildArtifacts
    from webcompy_cli._server import create_asgi_app

    artifacts = BuildArtifacts(
        app_version="1.2.3",
        wheel_filename="test.whl",
        app_package_files={"test.whl": (b"x", "application/zip")},
    )
    with (
        patch("webcompy_cli._server.resolve_build_artifacts", return_value=artifacts),
        patch("webcompy_cli._server.get_static_files", return_value=static_files),
    ):
        return create_asgi_app(app, build_config, mode="prod")


class TestServerManifestServing:
    @pytest.mark.asyncio
    async def test_serves_manifest_at_root(self, tmp_path):
        import httpx

        app = _make_app()
        pwa = PWAConfig(enabled=True, manifest=ManifestConfig(name="Served App", theme_color="#123456"))
        build_config = _make_build_config(tmp_path, pwa)
        serving = _create_serving(app, build_config)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=serving.asgi), base_url="http://test") as client:
            response = await client.get(f"/{MANIFEST_FILENAME}")
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("application/manifest+json")
        assert response.json()["name"] == "Served App"

    @pytest.mark.asyncio
    async def test_serves_manifest_under_prefix(self, tmp_path):
        import httpx

        app = _make_app(base_url="/pwa/")
        pwa = PWAConfig(enabled=True, manifest=ManifestConfig(name="Prefixed"))
        build_config = _make_build_config(tmp_path, pwa)
        serving = _create_serving(app, build_config)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=serving.asgi), base_url="http://test") as client:
            response = await client.get("/pwa/manifest.webmanifest")
            unprefixed = await client.get("/manifest.webmanifest")
        assert response.status_code == 200
        assert response.json()["scope"] == "/pwa/"
        assert unprefixed.status_code == 200

    @pytest.mark.asyncio
    async def test_disabled_returns_404(self, tmp_path):
        import httpx

        app = _make_app()
        build_config = _make_build_config(tmp_path, PWAConfig())
        serving = _create_serving(app, build_config)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=serving.asgi), base_url="http://test") as client:
            response = await client.get(f"/{MANIFEST_FILENAME}")
        assert response.status_code == 404

    def test_static_collision_warns(self, tmp_path, capsys):
        app = _make_app()
        pwa = PWAConfig(enabled=True, manifest=ManifestConfig(name="A"))
        build_config = _make_build_config(tmp_path, pwa)
        _create_serving(app, build_config, static_files=(MANIFEST_FILENAME,))
        assert "shadowed" in capsys.readouterr().err
