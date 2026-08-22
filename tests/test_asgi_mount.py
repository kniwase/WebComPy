from __future__ import annotations

import sys
import types
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


def _make_mount_fetch_root():
    from webcompy.components import define_component
    from webcompy.elements import html

    @define_component("mount-fetch-root")
    def MountFetchRoot(context):
        from webcompy.ajax import HttpClient
        from webcompy.components._hooks import use_async_result

        result = use_async_result(lambda: HttpClient.get("/api/users"))
        return html.DIV(
            {"data-testid": "mount-fetch-root"},
            result.data.value.text if result.data.value else "",
        )

    return MountFetchRoot


def _make_mount_fetch_root_with_query():
    from webcompy.components import define_component
    from webcompy.elements import html

    @define_component("mount-fetch-root-with-query")
    def MountFetchRootWithQuery(context):
        from webcompy.ajax import HttpClient
        from webcompy.components._hooks import use_async_result

        result = use_async_result(lambda: HttpClient.get("/api/users", query_params={"page": "2"}))
        return html.DIV(
            {"data-testid": "mount-fetch-root"},
            result.data.value.text if result.data.value else "",
        )

    return MountFetchRootWithQuery


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

    def test_non_dict_factory_return_rejected(self, tmp_path: Path) -> None:
        build_config = _make_build_config(tmp_path, mounts=lambda: ["/api"])
        app = _make_app()

        with pytest.raises(WebComPyException, match="must return a dict"):
            _create_serving(app, build_config)


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

    @define_component("test-page")
    def TestPage(ctx):
        return html.DIV({})

    return TestPage


class TestMountSelfSiteFetchDuringSsr:
    def test_blocked_paths_contain_pages_but_never_mount_prefixes(self, tmp_path: Path) -> None:
        api_app = _make_api_app()
        build_config = _make_build_config(tmp_path, mounts=lambda: {"/api": api_app})
        app = _make_app(
            router=_make_router(
                [
                    {"path": "/", "component": _make_page_component()},
                    {"path": "/admin", "component": _make_page_component()},
                ]
            )
        )

        _create_serving(app, build_config)

        port = app._server_fetch_port
        assert port is not None
        assert port._blocked_paths == ["", "admin"]
        assert all(not p.startswith("/api") for p in port._blocked_paths)
        assert port._mount_prefixes == ["/api"]

    @pytest.mark.asyncio
    async def test_context_clones_share_asgi_client_but_not_response_cache(self, tmp_path: Path) -> None:
        from webcompy.ports._keys import FETCH_PORT_KEY

        api_app = _make_api_app()
        build_config = _make_build_config(tmp_path, mounts=lambda: {"/api": api_app})
        app = _make_app()

        _create_serving(app, build_config)

        port = app._server_fetch_port
        assert port is not None
        assert port._self_site_client is not None

        ctx1 = app.create_render_context("/")
        ctx2 = app.create_render_context("/")
        try:
            port1 = ctx1.di_scope.inject(FETCH_PORT_KEY)
            port2 = ctx2.di_scope.inject(FETCH_PORT_KEY)
            assert port1 is not port
            assert port1._self_site_client is port._self_site_client, (
                "context clones must share the prototype's ASGI client"
            )
            assert port2._self_site_client is port._self_site_client
            assert port1._response_cache is not port._response_cache
            assert port2._response_cache is not port1._response_cache
        finally:
            ctx2.dispose()
            ctx1.dispose()

    @pytest.mark.asyncio
    async def test_fetch_to_mount_populates_transfer_cache_under_non_root_base_url(self, tmp_path: Path) -> None:
        from webcompy.app._app import WebComPyApp
        from webcompy.app._config import WebComPyAppConfig
        from webcompy.di import inject
        from webcompy.ports._keys import ASYNC_SCHEDULER_PORT_KEY, FETCH_PORT_KEY

        api_app = _make_api_app()
        build_config = _make_build_config(tmp_path, mounts=lambda: {"/api": api_app})
        app = WebComPyApp(
            root_component=_make_mount_fetch_root(),
            config=WebComPyAppConfig(base_url="/myapp/"),
        )

        serving = _create_serving(app, build_config)

        port = app._server_fetch_port
        assert port is not None
        assert port._mount_prefixes == ["/api"]
        assert all(not p.startswith("/api") for p in port._blocked_paths)

        ctx = app.create_render_context("/")
        ctx_port = ctx.di_scope.inject(FETCH_PORT_KEY)
        try:
            scheduler = inject(ASYNC_SCHEDULER_PORT_KEY)
            await scheduler.await_pending()
            html_str = await serving.html_generator(ctx)
        finally:
            ctx.dispose()

        assert "/api/users" in ctx_port._response_cache
        cached = ctx_port._response_cache["/api/users"]
        assert cached.status_code == 200
        assert cached.json() == {"path": "/api/users"}
        assert "/api/users" in ctx_port.get_transfer_data()
        assert "mount-fetch-root" in html_str

    @pytest.mark.asyncio
    async def test_fetch_to_mount_with_default_base_url(self, tmp_path: Path) -> None:
        from webcompy.app._app import WebComPyApp
        from webcompy.app._config import WebComPyAppConfig
        from webcompy.di import inject
        from webcompy.ports._keys import ASYNC_SCHEDULER_PORT_KEY, FETCH_PORT_KEY

        api_app = _make_api_app()
        build_config = _make_build_config(tmp_path, mounts=lambda: {"/api": api_app})
        app = WebComPyApp(
            root_component=_make_mount_fetch_root(),
            config=WebComPyAppConfig(base_url="/"),
        )

        serving = _create_serving(app, build_config)

        port = app._server_fetch_port
        assert port is not None

        ctx = app.create_render_context("/")
        ctx_port = ctx.di_scope.inject(FETCH_PORT_KEY)
        try:
            scheduler = inject(ASYNC_SCHEDULER_PORT_KEY)
            await scheduler.await_pending()
            html_str = await serving.html_generator(ctx)
        finally:
            ctx.dispose()

        assert "/api/users" in ctx_port._response_cache
        assert "/api/users" in ctx_port.get_transfer_data()
        assert ctx_port._response_cache["/api/users"].json() == {"path": "/api/users"}
        assert "mount-fetch-root" in html_str

    @pytest.mark.asyncio
    async def test_fetch_to_mount_with_query_params_under_non_root_base_url(self, tmp_path: Path) -> None:
        from webcompy.app._app import WebComPyApp
        from webcompy.app._config import WebComPyAppConfig
        from webcompy.di import inject
        from webcompy.ports._keys import ASYNC_SCHEDULER_PORT_KEY, FETCH_PORT_KEY

        async def users_handler(request):
            return JSONResponse({"path": str(request.url.path), "query": str(request.url.query)})

        api_app = Starlette(routes=[Route("/users", endpoint=users_handler)])
        build_config = _make_build_config(tmp_path, mounts=lambda: {"/api": api_app})
        app = WebComPyApp(
            root_component=_make_mount_fetch_root_with_query(),
            config=WebComPyAppConfig(base_url="/myapp/"),
        )

        serving = _create_serving(app, build_config)

        port = app._server_fetch_port
        assert port is not None
        assert port._mount_prefixes == ["/api"]

        ctx = app.create_render_context("/")
        ctx_port = ctx.di_scope.inject(FETCH_PORT_KEY)
        try:
            scheduler = inject(ASYNC_SCHEDULER_PORT_KEY)
            await scheduler.await_pending()
            html_str = await serving.html_generator(ctx)
        finally:
            ctx.dispose()

        assert "/api/users?page=2" in ctx_port._response_cache
        cached = ctx_port._response_cache["/api/users?page=2"]
        assert cached.status_code == 200
        assert cached.json() == {"path": "/api/users", "query": "page=2"}
        assert "/api/users?page=2" in ctx_port.get_transfer_data()
        assert "mount-fetch-root" in html_str


class TestMountSsg:
    def test_ssg_with_mounts_completes_and_excludes_mount_paths(self, tmp_path: Path) -> None:
        from webcompy_cli._generate import generate_static_site
        from webcompy_server import configure_server_context

        pkg = _make_app_pkg(tmp_path)
        mod_path = pkg / "_app_mod.py"
        api_app = _make_api_app()
        from webcompy.app._app import WebComPyApp
        from webcompy.app._config import WebComPyAppConfig

        app = WebComPyApp(
            root_component=_make_mount_fetch_root(),
            config=WebComPyAppConfig(base_url="/"),
        )

        fake_mod = types.ModuleType("fake_app_mod")
        fake_mod.__file__ = str(mod_path)
        fake_mod.app = app
        sys.modules["fake_app_mod"] = fake_mod
        build_config = WebComPyBuildConfig(fake_mod)
        build_config.server.mounts = lambda: {"/api": api_app}

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
        assert not (pkg / "dist" / "api").exists()
        html_text = index_html.read_text(encoding="utf8")
        assert "/api/users" in html_text
