from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import httpx
import pytest

from webcompy_cli._build import BuildArtifacts
from webcompy_cli.config._build_config import WebComPyBuildConfig


def _make_app_pkg(tmp_path: Path) -> Path:
    pkg = tmp_path / "app"
    pkg.mkdir()
    mod_path = pkg / "_app_mod.py"
    mod_path.write_text("app = None\n")
    return pkg


def _make_build_config(tmp_path: Path) -> WebComPyBuildConfig:
    pkg = _make_app_pkg(tmp_path)
    mod_path = pkg / "_app_mod.py"
    import importlib.util

    spec = importlib.util.spec_from_file_location("_ephemeral_app", mod_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return WebComPyBuildConfig(app_module=mod)


def _make_artifacts(tmp_path: Path) -> BuildArtifacts:
    return BuildArtifacts(
        app_version="test-version",
        wheel_filename="test.whl",
        app_package_files={"test.whl": (b"x", "application/zip")},
        resource_allow_list=None,
    )


def _make_router_root():
    from webcompy.components import define_component
    from webcompy.elements import html
    from webcompy.router import RouterView

    @define_component("app-root")
    def AppRoot(ctx):
        return html.DIV({}, RouterView())

    return AppRoot


def _make_cookie_setting_page():
    from datetime import UTC, datetime

    from webcompy.components import define_component
    from webcompy.di import inject
    from webcompy.elements import html
    from webcompy.ports._keys import COOKIE_PORT_KEY

    @define_component("test-page")
    def TestPage(ctx):
        inject(COOKIE_PORT_KEY).set(
            "session",
            "abc",
            max_age=3600,
            expires=datetime(2024, 1, 1, tzinfo=UTC),
            path="/",
            domain="example.com",
            secure=True,
            httponly=True,
            samesite="Strict",
        )
        return html.DIV({})

    return TestPage


def _make_router(pages: list[dict], mode: str = "history"):
    from webcompy.router._router import Router

    return Router(*pages, mode=mode, preload=False)


def _make_app(router=None):
    from webcompy.app._app import WebComPyApp
    from webcompy.app._config import WebComPyAppConfig

    return WebComPyApp(
        root_component=_make_router_root(),
        router=router,
        config=WebComPyAppConfig(base_url="/"),
    )


def _create_serving(app, build_config, *, mode="prod"):
    from webcompy_cli._server import create_asgi_app
    from webcompy_server import configure_server_context

    with (
        patch(
            "webcompy_cli._server.resolve_build_artifacts", return_value=_make_artifacts(build_config.app_package_path)
        ),
        patch("webcompy_cli._server.get_static_files", return_value=()),
    ):
        configure_server_context(app)
        return create_asgi_app(app, build_config, mode=mode)


class TestSsrSetCookieHeaders:
    @pytest.mark.asyncio
    async def test_ssr_response_emits_set_cookie_headers(self, tmp_path: Path) -> None:
        app = _make_app(router=_make_router([{"path": "/", "component": _make_cookie_setting_page()}]))
        build_config = _make_build_config(tmp_path)
        serving = _create_serving(app, build_config)

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=serving.asgi), base_url="http://test") as client:
            response = await client.get("/", headers={"Accept": "text/html"})

        assert response.status_code == 200
        set_cookies = response.headers.get_list("set-cookie")
        assert len(set_cookies) == 1
        header = set_cookies[0]
        assert header.startswith("session=abc")
        assert "Max-Age=3600" in header
        assert "expires=Mon, 01 Jan 2024 00:00:00 GMT" in header
        assert "Domain=example.com" in header
        assert "Secure" in header
        assert "HttpOnly" in header
        assert "SameSite=Strict" in header
        assert "Path=/" in header

    @pytest.mark.asyncio
    async def test_ssr_response_without_cookie_writes_has_no_set_cookie(self, tmp_path: Path) -> None:
        from webcompy.components import define_component
        from webcompy.elements import html

        @define_component("test-page")
        def TestPage(ctx):
            return html.DIV({})

        app = _make_app(router=_make_router([{"path": "/", "component": TestPage}]))
        build_config = _make_build_config(tmp_path)
        serving = _create_serving(app, build_config)

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=serving.asgi), base_url="http://test") as client:
            response = await client.get("/", headers={"Accept": "text/html"})

        assert response.status_code == 200
        assert "set-cookie" not in response.headers

    @pytest.mark.asyncio
    async def test_hash_mode_does_not_emit_set_cookie(self, tmp_path: Path) -> None:
        app = _make_app(router=_make_router([{"path": "/", "component": _make_cookie_setting_page()}], mode="hash"))
        build_config = _make_build_config(tmp_path)
        serving = _create_serving(app, build_config)

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=serving.asgi), base_url="http://test") as client:
            response = await client.get("/")

        assert response.status_code == 200
        assert "set-cookie" not in response.headers


class TestSsgCookieWrites:
    def test_ssg_ignores_cookie_writes(self, tmp_path: Path) -> None:
        import sys
        import types

        from webcompy.app._app import WebComPyApp
        from webcompy.app._config import WebComPyAppConfig
        from webcompy_cli._generate import generate_static_site
        from webcompy_server import configure_server_context

        pkg = _make_app_pkg(tmp_path)
        mod_path = pkg / "_app_mod.py"
        app = WebComPyApp(
            root_component=_make_cookie_setting_root(),
            config=WebComPyAppConfig(base_url="/"),
        )

        fake_mod = types.ModuleType("fake_app_mod")
        fake_mod.__file__ = str(mod_path)
        fake_mod.app = app
        sys.modules["fake_app_mod"] = fake_mod
        build_config = WebComPyBuildConfig(fake_mod)

        saved_argv = sys.argv
        sys.argv = ["webcompy", "generate"]
        try:
            with (
                patch("webcompy_cli._generate.discover_config", return_value=build_config),
                patch(
                    "webcompy_cli._server.resolve_build_artifacts",
                    return_value=_make_artifacts(pkg),
                ),
                patch("webcompy_cli._server.get_static_files", return_value=()),
                patch("webcompy_cli._generate.get_static_files", return_value=()),
                patch("webcompy.ui._styles.get_styles_files", return_value={}, create=True),
            ):

                async def _run() -> None:
                    configure_server_context(app)
                    await generate_static_site()

                import asyncio

                asyncio.run(_run())
        finally:
            sys.modules.pop("fake_app_mod", None)
            sys.argv = saved_argv

        index_html = pkg / "dist" / "index.html"
        assert index_html.exists()
        html_text = index_html.read_text(encoding="utf8")
        assert "cookie-root" in html_text


def _make_cookie_setting_root():
    from webcompy.components import define_component
    from webcompy.di import inject
    from webcompy.elements import html
    from webcompy.ports._keys import COOKIE_PORT_KEY

    @define_component("app-root")
    def AppRoot(ctx):
        inject(COOKIE_PORT_KEY).set("session", "abc")
        return html.DIV({}, "cookie-root")

    return AppRoot
