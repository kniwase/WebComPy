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

    def setup(ctx):
        return html.DIV({}, RouterView())

    setup.__name__ = "AppRoot"
    return define_component(setup)


def _make_cookie_setting_page():
    from webcompy.components import define_component
    from webcompy.di import inject
    from webcompy.elements import html
    from webcompy.ports._keys import COOKIE_PORT_KEY

    def setup(ctx):
        inject(COOKIE_PORT_KEY).set(
            "session",
            "abc",
            max_age=3600,
            secure=True,
            httponly=True,
            samesite="Strict",
            path="/",
        )
        return html.DIV({})

    setup.__name__ = "Page"
    return define_component(setup)


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
        assert "Secure" in header
        assert "HttpOnly" in header
        assert "SameSite=Strict" in header
        assert "Path=/" in header

    @pytest.mark.asyncio
    async def test_ssr_response_without_cookie_writes_has_no_set_cookie(self, tmp_path: Path) -> None:
        from webcompy.components import define_component
        from webcompy.elements import html

        def setup(ctx):
            return html.DIV({})

        setup.__name__ = "Page"
        app = _make_app(router=_make_router([{"path": "/", "component": define_component(setup)}]))
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
