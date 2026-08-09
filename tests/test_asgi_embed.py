from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import httpx
import pytest
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

from webcompy_cli._build import BuildArtifacts
from webcompy_cli.config._build_config import WebComPyBuildConfig


def _make_app_pkg(tmp_path: Path, files: dict[str, str] | None = None) -> Path:
    pkg = tmp_path / "app"
    pkg.mkdir()
    for rel, content in (files or {}).items():
        target = pkg / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    mod_path = pkg / "_app_mod.py"
    mod_path.write_text("app = None\n")
    return pkg


def _make_build_config(pkg: Path) -> WebComPyBuildConfig:
    import importlib.util

    mod_path = pkg / "_app_mod.py"
    spec = importlib.util.spec_from_file_location("_ephemeral_app", mod_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return WebComPyBuildConfig(app_module=mod)


def _make_artifacts(pkg: Path, *, resource_allow_list: frozenset[str] | None = None) -> BuildArtifacts:
    return BuildArtifacts(
        app_version="test-version",
        wheel_filename="test.whl",
        app_package_files={"test.whl": (b"x", "application/zip")},
        resource_allow_list=resource_allow_list,
    )


def _make_app(base_url: str = "/admin/", router=None, root_component=None):
    from webcompy.app._app import WebComPyApp
    from webcompy.app._config import WebComPyAppConfig

    return WebComPyApp(
        root_component=root_component or (lambda _: None),
        router=router,
        config=WebComPyAppConfig(base_url=base_url),
    )


def _make_router(pages: list[dict], mode: str = "history"):
    from webcompy.elements import html
    from webcompy.router._router import Router

    def setup(ctx):
        return html.DIV({})

    setup.__name__ = "Page"
    return Router(*pages, mode=mode, preload=False)


def _make_page_component():
    from webcompy.components import define_component
    from webcompy.elements import html

    def setup(ctx):
        return html.DIV({})

    setup.__name__ = "Page"
    return define_component(setup)


def _make_fetch_root():
    from webcompy.components import define_component
    from webcompy.elements import html

    @define_component
    def _FetchRoot(context):
        from webcompy.ajax import HttpClient
        from webcompy.components._hooks import use_async_result

        result = use_async_result(lambda: HttpClient.get("/api/items"))
        return html.DIV(
            {"data-testid": "embed-fetch-root"},
            result.data.value.text if result.data.value else "",
        )

    return _FetchRoot


def _make_api_handler():
    async def items_handler(request):
        return JSONResponse({"path": str(request.url.path)})

    return items_handler


def _create_serving(app, build_config, *, artifacts: BuildArtifacts | None = None):
    from webcompy_cli._server import create_asgi_app
    from webcompy_server import configure_server_context

    with (
        patch(
            "webcompy_cli._server.resolve_build_artifacts",
            return_value=artifacts or _make_artifacts(build_config.app_package_path),
        ),
        patch("webcompy_cli._server.get_static_files", return_value=()),
    ):
        configure_server_context(app)
        return create_asgi_app(app, build_config, mode="prod")


def _make_host(serving_asgi) -> Starlette:
    return Starlette(
        routes=[
            Route("/api/items", endpoint=_make_api_handler()),
            Mount("/admin", app=serving_asgi),
        ]
    )


class TestEmbeddedServing:
    @pytest.mark.asyncio
    async def test_embedded_ssr_page_render(self, tmp_path: Path) -> None:
        from webcompy_server import configure_server_context

        pkg = _make_app_pkg(tmp_path)
        build_config = _make_build_config(pkg)
        app = _make_app(
            router=_make_router(
                [
                    {"path": "/", "component": _make_page_component()},
                    {"path": "/users", "component": _make_page_component()},
                ]
            )
        )
        serving = _create_serving(app, build_config)
        configure_server_context(app, root_app=_make_host(serving.asgi))
        host = _make_host(serving.asgi)

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=host), base_url="http://test") as client:
            response = await client.get("/admin/", headers={"Accept": "text/html"})
            users_response = await client.get("/admin/users", headers={"Accept": "text/html"})

        assert response.status_code == 200
        assert 'base href="/admin/"' in response.text
        assert "/admin/_webcompy-ui/index.css" in response.text
        assert users_response.status_code == 200

    @pytest.mark.asyncio
    async def test_framework_endpoint_under_prefix(self, tmp_path: Path) -> None:
        from webcompy_server import configure_server_context

        pkg = _make_app_pkg(tmp_path)
        build_config = _make_build_config(pkg)
        app = _make_app()
        serving = _create_serving(app, build_config)
        configure_server_context(app, root_app=_make_host(serving.asgi))
        host = _make_host(serving.asgi)

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=host), base_url="http://test") as client:
            response = await client.get("/admin/_webcompy-app-package/test.whl")

        assert response.status_code == 200
        assert response.content == b"x"

    @pytest.mark.asyncio
    async def test_host_route_unaffected(self, tmp_path: Path) -> None:
        from webcompy_server import configure_server_context

        pkg = _make_app_pkg(tmp_path)
        build_config = _make_build_config(pkg)
        app = _make_app()
        serving = _create_serving(app, build_config)
        configure_server_context(app, root_app=_make_host(serving.asgi))
        host = _make_host(serving.asgi)

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=host), base_url="http://test") as client:
            response = await client.get("/api/items")

        assert response.status_code == 200
        assert response.json() == {"path": "/api/items"}

    @pytest.mark.asyncio
    async def test_resource_endpoint_under_prefix(self, tmp_path: Path) -> None:
        from webcompy_server import configure_server_context

        pkg = _make_app_pkg(tmp_path, {"data.txt": "hello"})
        build_config = _make_build_config(pkg)
        artifacts = _make_artifacts(pkg, resource_allow_list=frozenset({"data.txt"}))

        app = _make_app()
        serving = _create_serving(app, build_config, artifacts=artifacts)
        configure_server_context(app, root_app=_make_host(serving.asgi))
        host = _make_host(serving.asgi)

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=host), base_url="http://test") as client:
            response = await client.get("/admin/_webcompy-resource/data.txt")

        assert response.status_code == 200
        assert response.text == "hello"

    @pytest.mark.asyncio
    async def test_resource_endpoint_standalone_prefixed_unchanged(self, tmp_path: Path) -> None:
        pkg = _make_app_pkg(tmp_path, {"data.txt": "hello"})
        build_config = _make_build_config(pkg)
        artifacts = _make_artifacts(pkg, resource_allow_list=frozenset({"data.txt"}))

        app = _make_app(base_url="/myapp/")
        serving = _create_serving(app, build_config, artifacts=artifacts)

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=serving.asgi), base_url="http://test") as client:
            response = await client.get("/myapp/_webcompy-resource/data.txt")

        assert response.status_code == 200
        assert response.text == "hello"

    @pytest.mark.asyncio
    async def test_hash_mode_under_prefix(self, tmp_path: Path) -> None:
        from webcompy_server import configure_server_context

        pkg = _make_app_pkg(tmp_path)
        build_config = _make_build_config(pkg)
        app = _make_app(router=_make_router([], mode="hash"))
        serving = _create_serving(app, build_config)
        configure_server_context(app, root_app=_make_host(serving.asgi))
        host = _make_host(serving.asgi)

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=host), base_url="http://test") as client:
            response = await client.get("/admin/", headers={"Accept": "text/html"})

        assert response.status_code == 200
        assert 'base href="/admin/"' in response.text


class TestEmbeddedSelfSiteFetch:
    @pytest.mark.asyncio
    async def test_embedded_relative_path_resolution(self) -> None:
        from webcompy_server.ports._fetch import ServerFetchPort

        port = ServerFetchPort()
        port.configure(Starlette(routes=[]), base_url="/admin/", embedded=True)

        assert port._resolve_self_site_path("./api/items") == "/admin/api/items"
        assert port._resolve_self_site_path("/api/items") == "/api/items"
        assert port._resolve_self_site_path("./") == "/admin/"

    @pytest.mark.asyncio
    async def test_fetch_to_host_api_during_ssr(self, tmp_path: Path) -> None:
        from webcompy.di import inject
        from webcompy.ports._keys import ASYNC_SCHEDULER_PORT_KEY
        from webcompy_server import configure_server_context

        pkg = _make_app_pkg(tmp_path)
        build_config = _make_build_config(pkg)
        app = _make_app(root_component=_make_fetch_root())
        serving = _create_serving(app, build_config)
        configure_server_context(app, root_app=_make_host(serving.asgi))

        port = app._server_fetch_port
        assert port is not None
        assert port._embedded is True

        ctx = app.create_render_context("/")
        try:
            scheduler = inject(ASYNC_SCHEDULER_PORT_KEY)
            await scheduler.await_pending()
            html_str = await serving.html_generator(ctx)
        finally:
            ctx.dispose()

        assert "/api/items" in port._response_cache
        cached = port._response_cache["/api/items"]
        assert cached.status_code == 200
        assert cached.json() == {"path": "/api/items"}
        assert "/api/items" in port.get_transfer_data()
        assert "embed-fetch-root" in html_str


class TestEmbeddedBlockedPaths:
    @pytest.mark.asyncio
    async def test_page_paths_prefixed_and_host_api_not_blocked(self, tmp_path: Path) -> None:
        from webcompy_server import configure_server_context

        pkg = _make_app_pkg(tmp_path)
        build_config = _make_build_config(pkg)
        app = _make_app(
            router=_make_router(
                [
                    {"path": "/", "component": _make_page_component()},
                    {"path": "/users", "component": _make_page_component()},
                ]
            )
        )
        serving = _create_serving(app, build_config)
        configure_server_context(app, root_app=_make_host(serving.asgi))

        port = app._server_fetch_port
        assert port is not None
        assert port._blocked_paths == ["admin", "admin/users"]

        blocked_page = await port.fetch("/admin/users")
        assert blocked_page.status_code == 500
        assert "blocked" in blocked_page.text

        blocked_root = await port.fetch("/admin")
        assert blocked_root.status_code == 500

        host_api = await port.fetch("/api/items")
        assert host_api.status_code == 200
        assert host_api.json() == {"path": "/api/items"}


class TestDefaultConfiguration:
    @pytest.mark.asyncio
    async def test_default_configuration_unchanged(self, tmp_path: Path) -> None:
        pkg = _make_app_pkg(tmp_path)
        build_config = _make_build_config(pkg)
        app = _make_app()
        serving = _create_serving(app, build_config)

        port = app._server_fetch_port
        assert port is not None
        assert port._embedded is False
        assert port._asgi_app is serving.asgi
        assert port._blocked_paths == []

    @pytest.mark.asyncio
    async def test_root_app_configured_port_replaces_cli_port(self, tmp_path: Path) -> None:
        from webcompy_server import configure_server_context

        pkg = _make_app_pkg(tmp_path)
        build_config = _make_build_config(pkg)
        app = _make_app()
        serving = _create_serving(app, build_config)

        cli_port = app._server_fetch_port
        assert cli_port is not None
        assert cli_port._asgi_app is serving.asgi

        host = _make_host(serving.asgi)
        configure_server_context(app, root_app=host)

        embedded_port = app._server_fetch_port
        assert embedded_port is not cli_port
        assert embedded_port is not None
        assert embedded_port._asgi_app is host
        assert embedded_port._embedded is True
