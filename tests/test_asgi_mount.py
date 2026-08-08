from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock, patch

import httpx
import pytest
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

from webcompy.exception import WebComPyException
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
    spec.loader.exec_module(mod)
    return pkg


def _make_build_config(tmp_path: Path, mounts: object | None = None) -> WebComPyBuildConfig:
    pkg = _make_app_pkg(tmp_path)
    mod_path = pkg / "_app_mod.py"
    import importlib.util

    spec = importlib.util.spec_from_file_location("_ephemeral_app", mod_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    config = WebComPyBuildConfig(app_module=mod)
    if mounts is not None:
        config.server.mounts = mounts
    return config


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


def _make_api_app() -> Starlette:
    async def user_handler(request):
        return JSONResponse({"path": request.url.path})

    return Starlette(
        routes=[
            Route("/users", endpoint=user_handler),
        ]
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


class TestMountsCallableInvocation:
    def test_callable_invoked_once_on_serving_construction(self, tmp_path: Path) -> None:
        api_app = _make_api_app()
        factory = Mock(return_value={"/api": api_app})
        build_config = _make_build_config(tmp_path, mounts=factory)
        app = _make_app()

        _create_serving(app, build_config)

        factory.assert_called_once_with()

    def test_no_mounts_callable_not_invoked(self, tmp_path: Path) -> None:
        build_config = _make_build_config(tmp_path)
        app = _make_app()

        _create_serving(app, build_config)

        assert build_config.server.mounts is None


class TestMountRouteInsertion:
    def test_mount_inserted_before_catch_all(self, tmp_path: Path) -> None:
        api_app = _make_api_app()
        build_config = _make_build_config(tmp_path, mounts=lambda: {"/api": api_app})
        app = _make_app(router=_make_router([{"path": "/", "component": _make_page_component()}]))

        serving = _create_serving(app, build_config)

        routes = list(serving.asgi.routes)
        mount_index = next(i for i, r in enumerate(routes) if isinstance(r, Mount))
        catch_all_index = next(i for i, r in enumerate(routes) if isinstance(r, Route) and r.path == "/{path:path}")
        assert mount_index < catch_all_index

    @pytest.mark.asyncio
    async def test_mount_handles_requests_before_ssr(self, tmp_path: Path) -> None:
        api_app = _make_api_app()
        build_config = _make_build_config(tmp_path, mounts=lambda: {"/api": api_app})
        app = _make_app()

        serving = _create_serving(app, build_config)

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=serving.asgi), base_url="http://test") as client:
            response = await client.get("/api/users")

        assert response.status_code == 200
        assert response.json() == {"path": "/api/users"}

    @pytest.mark.asyncio
    async def test_unmatched_path_inside_mount_returns_mount_own_404(self, tmp_path: Path) -> None:
        api_app = _make_api_app()
        build_config = _make_build_config(tmp_path, mounts=lambda: {"/api": api_app})
        app = _make_app()

        serving = _create_serving(app, build_config)

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=serving.asgi), base_url="http://test") as client:
            response = await client.get("/api/nonexistent", headers={"Accept": "text/html"})

        assert response.status_code == 404
        assert "text/html" not in response.headers.get("content-type", "").lower()

    @pytest.mark.asyncio
    async def test_mount_works_in_hash_mode(self, tmp_path: Path) -> None:
        api_app = _make_api_app()
        build_config = _make_build_config(tmp_path, mounts=lambda: {"/api": api_app})
        app = _make_app(router=_make_router([], mode="hash"))

        serving = _create_serving(app, build_config)

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=serving.asgi), base_url="http://test") as client:
            response = await client.get("/api/users")

        assert response.status_code == 200
        assert response.json() == {"path": "/api/users"}


class TestMountCollisionDetection:
    def test_reserved_prefix_rejected(self, tmp_path: Path) -> None:
        api_app = _make_api_app()
        build_config = _make_build_config(tmp_path, mounts=lambda: {"/_webcompy-api": api_app})
        app = _make_app()

        with pytest.raises(WebComPyException, match="_webcompy-api"):
            _create_serving(app, build_config)

    def test_page_route_exact_collision_rejected(self, tmp_path: Path) -> None:
        api_app = _make_api_app()
        build_config = _make_build_config(tmp_path, mounts=lambda: {"/admin": api_app})
        app = _make_app(router=_make_router([{"path": "/admin", "component": _make_page_component()}]))

        with pytest.raises(WebComPyException, match="/admin"):
            _create_serving(app, build_config)

    def test_parameterized_page_route_collision_rejected(self, tmp_path: Path) -> None:
        api_app = _make_api_app()
        build_config = _make_build_config(tmp_path, mounts=lambda: {"/users": api_app})
        app = _make_app(router=_make_router([{"path": "/users/{uid}", "component": _make_page_component()}]))

        with pytest.raises(WebComPyException, match="/users"):
            _create_serving(app, build_config)

    def test_root_mount_rejected(self, tmp_path: Path) -> None:
        api_app = _make_api_app()
        build_config = _make_build_config(tmp_path, mounts=lambda: {"/": api_app})
        app = _make_app()

        with pytest.raises(WebComPyException, match="shadow"):
            _create_serving(app, build_config)

    def test_empty_prefix_rejected(self, tmp_path: Path) -> None:
        api_app = _make_api_app()
        build_config = _make_build_config(tmp_path, mounts=lambda: {"": api_app})
        app = _make_app()

        with pytest.raises(WebComPyException, match="shadow"):
            _create_serving(app, build_config)

    def test_non_colliding_mount_accepted(self, tmp_path: Path) -> None:
        api_app = _make_api_app()
        build_config = _make_build_config(tmp_path, mounts=lambda: {"/api": api_app})
        app = _make_app(router=_make_router([{"path": "/users", "component": _make_page_component()}]))

        serving = _create_serving(app, build_config)

        assert any(isinstance(r, Mount) for r in serving.asgi.routes)

    def test_mount_under_parameterized_page_not_collision(self, tmp_path: Path) -> None:
        api_app = _make_api_app()
        build_config = _make_build_config(tmp_path, mounts=lambda: {"/users/list": api_app})
        app = _make_app(router=_make_router([{"path": "/users/{uid}", "component": _make_page_component()}]))

        serving = _create_serving(app, build_config)

        assert any(isinstance(r, Mount) for r in serving.asgi.routes)

    def test_similar_but_distinct_prefix_not_collision(self, tmp_path: Path) -> None:
        api_app = _make_api_app()
        build_config = _make_build_config(tmp_path, mounts=lambda: {"/api": api_app})
        app = _make_app(router=_make_router([{"path": "/apis", "component": _make_page_component()}]))

        serving = _create_serving(app, build_config)

        assert any(isinstance(r, Mount) for r in serving.asgi.routes)


class TestMountSsrIntegration:
    @pytest.mark.asyncio
    async def test_page_route_still_renders_alongside_mount(self, tmp_path: Path) -> None:
        api_app = _make_api_app()
        build_config = _make_build_config(tmp_path, mounts=lambda: {"/api": api_app})
        app = _make_app(router=_make_router([{"path": "/", "component": _make_page_component()}]))

        serving = _create_serving(app, build_config)

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=serving.asgi), base_url="http://test") as client:
            response = await client.get("/", headers={"Accept": "text/html"})

        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "").lower()


def _make_page_component():
    from webcompy.components import define_component
    from webcompy.elements import html

    def setup(ctx):
        return html.DIV({})

    setup.__name__ = "Page"
    return define_component(setup)
