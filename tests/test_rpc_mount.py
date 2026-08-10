from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import httpx
import pytest
from starlette.routing import Route

from webcompy_cli._build import BuildArtifacts
from webcompy_cli.config._build_config import WebComPyBuildConfig


def _make_app_pkg(tmp_path: Path) -> Path:
    pkg = tmp_path / "app"
    pkg.mkdir()
    mod_path = pkg / "_app_mod.py"
    mod_path.write_text("app = None\n")
    import importlib.util

    spec = importlib.util.spec_from_file_location("_ephemeral_app", mod_path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return pkg


def _make_build_config(tmp_path: Path) -> WebComPyBuildConfig:
    pkg = _make_app_pkg(tmp_path)
    mod_path = pkg / "_app_mod.py"
    import importlib.util

    spec = importlib.util.spec_from_file_location("_ephemeral_app", mod_path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return WebComPyBuildConfig(app_module=mod)


def _make_artifacts(tmp_path: Path) -> BuildArtifacts:
    return BuildArtifacts(
        app_version="test-version",
        wheel_filename="test.whl",
        app_package_files={"test.whl": (b"x", "application/zip")},
        resource_allow_list=None,
    )


def _make_app(router=None, base_url: str = "/"):
    from webcompy.app._app import WebComPyApp
    from webcompy.app._config import WebComPyAppConfig

    return WebComPyApp(
        root_component=lambda _: None,
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


def _add(a: int, b: int = 0) -> int:
    return a + b


def _rpc_paths(asgi) -> list[str]:
    return [route.path for route in asgi.routes if isinstance(route, Route) and route.methods == {"POST"}]


class TestEndpointPresence:
    def test_endpoint_absent_when_no_procedures(self, tmp_path: Path) -> None:
        build_config = _make_build_config(tmp_path)
        app = _make_app()

        serving = _create_serving(app, build_config)

        assert _rpc_paths(serving.asgi) == []

    def test_endpoint_present_when_procedures_registered(self, tmp_path: Path) -> None:
        build_config = _make_build_config(tmp_path)
        app = _make_app()
        app.rpc.register("add", _add)

        serving = _create_serving(app, build_config)

        assert "/_webcompy-rpc" in _rpc_paths(serving.asgi)


class TestEndpointRouting:
    @pytest.mark.asyncio
    async def test_post_to_default_path_handled(self, tmp_path: Path) -> None:
        build_config = _make_build_config(tmp_path)
        app = _make_app()
        app.rpc.register("add", _add)

        serving = _create_serving(app, build_config)

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=serving.asgi), base_url="http://test") as client:
            response = await client.post(
                "/_webcompy-rpc",
                json={"jsonrpc": "2.0", "method": "add", "params": {"a": 1, "b": 2}, "id": 1},
            )

        assert response.status_code == 200
        assert response.json() == {"jsonrpc": "2.0", "result": 3, "id": 1}

    @pytest.mark.asyncio
    async def test_get_to_endpoint_returns_405(self, tmp_path: Path) -> None:
        build_config = _make_build_config(tmp_path)
        app = _make_app()
        app.rpc.register("add", _add)

        serving = _create_serving(app, build_config)

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=serving.asgi), base_url="http://test") as client:
            response = await client.get("/_webcompy-rpc")

        assert response.status_code == 405

    @pytest.mark.asyncio
    async def test_custom_path_handled(self, tmp_path: Path) -> None:
        build_config = _make_build_config(tmp_path)
        app = _make_app()
        app.rpc.register("add", _add)
        app.rpc.set_path("/custom/rpc")

        serving = _create_serving(app, build_config)

        assert "/custom/rpc" in _rpc_paths(serving.asgi)

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=serving.asgi), base_url="http://test") as client:
            response = await client.post(
                "/custom/rpc",
                json={"jsonrpc": "2.0", "method": "add", "params": {"a": 1}, "id": 1},
            )

        assert response.json()["result"] == 1

    @pytest.mark.asyncio
    async def test_base_url_variant_reachable(self, tmp_path: Path) -> None:
        build_config = _make_build_config(tmp_path)
        app = _make_app(base_url="/myapp/")
        app.rpc.register("add", _add)

        serving = _create_serving(app, build_config)

        assert "/_webcompy-rpc" in _rpc_paths(serving.asgi)
        assert "/myapp/_webcompy-rpc" in _rpc_paths(serving.asgi)

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=serving.asgi), base_url="http://test") as client:
            response = await client.post(
                "/myapp/_webcompy-rpc",
                json={"jsonrpc": "2.0", "method": "add", "params": {"a": 1}, "id": 1},
            )

        assert response.json()["result"] == 1

    @pytest.mark.asyncio
    async def test_rpc_route_inserted_before_catch_all(self, tmp_path: Path) -> None:
        build_config = _make_build_config(tmp_path)
        app = _make_app(router=_make_router([{"path": "/", "component": _make_page_component()}]))
        app.rpc.register("add", _add)

        serving = _create_serving(app, build_config)

        routes = list(serving.asgi.routes)
        rpc_index = next(i for i, r in enumerate(routes) if isinstance(r, Route) and r.path == "/_webcompy-rpc")
        catch_all_index = next(i for i, r in enumerate(routes) if isinstance(r, Route) and r.path == "/{path:path}")
        assert rpc_index < catch_all_index

    @pytest.mark.asyncio
    async def test_page_still_renders_alongside_endpoint(self, tmp_path: Path) -> None:
        build_config = _make_build_config(tmp_path)
        app = _make_app(router=_make_router([{"path": "/", "component": _make_page_component()}]))
        app.rpc.register("add", _add)

        serving = _create_serving(app, build_config)

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=serving.asgi), base_url="http://test") as client:
            response = await client.get("/", headers={"Accept": "text/html"})

        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "").lower()


class TestFetchPortConfiguration:
    def test_prefixed_rpc_path_added_to_mount_prefixes_for_non_root_base(self, tmp_path: Path) -> None:
        build_config = _make_build_config(tmp_path)
        app = _make_app(base_url="/myapp/")
        app.rpc.register("add", _add)

        _create_serving(app, build_config)

        port = app._server_fetch_port
        assert port is not None
        assert "/myapp/_webcompy-rpc" in port._mount_prefixes

    def test_no_rpc_prefix_in_mount_prefixes_without_procedures(self, tmp_path: Path) -> None:
        build_config = _make_build_config(tmp_path)
        app = _make_app(base_url="/myapp/")

        _create_serving(app, build_config)

        port = app._server_fetch_port
        assert port is not None
        assert "/myapp/_webcompy-rpc" not in port._mount_prefixes

    def test_root_base_url_adds_no_prefixed_rpc_path(self, tmp_path: Path) -> None:
        build_config = _make_build_config(tmp_path)
        app = _make_app()
        app.rpc.register("add", _add)

        _create_serving(app, build_config)

        port = app._server_fetch_port
        assert port is not None
        assert port._mount_prefixes == []
