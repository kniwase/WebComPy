from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from webcompy.di import inject
from webcompy.ports._keys import ASYNC_SCHEDULER_PORT_KEY
from webcompy.rpc import call as rpc_call
from webcompy.rpc._errors import RpcError
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


def _make_rpc_fetch_root():
    from webcompy.components import define_component
    from webcompy.components._hooks import use_async_result
    from webcompy.elements import html

    @define_component("rpc-fetch-root")
    def RpcFetchRoot(context):
        result = use_async_result(lambda: rpc_call("add", {"a": 1, "b": 2}, result_type=int))
        return html.DIV(
            {"data-testid": "rpc-root"},
            str(result.data.value) if result.data.value is not None else "",
        )

    return RpcFetchRoot


def _make_rpc_fetch_root_no_transfer():
    from webcompy.components import define_component
    from webcompy.components._hooks import use_async_result
    from webcompy.elements import html

    @define_component("rpc-fetch-root-no-transfer")
    def RpcFetchRootNoTransfer(context):
        result = use_async_result(lambda: rpc_call("add", {"a": 1, "b": 2}, result_type=int), transfer=False)
        return html.DIV(
            {"data-testid": "rpc-root-no-transfer"},
            str(result.data.value) if result.data.value is not None else "",
        )

    return RpcFetchRootNoTransfer


def _add(a: int, b: int = 0) -> int:
    return a + b


def _boom() -> None:
    raise RuntimeError("boom")


async def _render(app, serving) -> str:
    ctx = app.create_render_context("/")
    try:
        scheduler = inject(ASYNC_SCHEDULER_PORT_KEY)
        await scheduler.await_pending()
        return await serving.html_generator(ctx)
    finally:
        ctx.dispose()


class TestSsrBake:
    @pytest.mark.asyncio
    async def test_rpc_during_ssr_is_baked(self, tmp_path: Path) -> None:
        from webcompy.app._app import WebComPyApp

        build_config = _make_build_config(tmp_path)
        app = WebComPyApp(root_component=_make_rpc_fetch_root())
        app.rpc.register("add", _add)
        serving = _create_serving(app, build_config)

        html_str = await _render(app, serving)

        port = app._server_fetch_port
        assert port is not None
        cache_keys = list(port._response_cache.keys())
        assert any(key.startswith("POST:/_webcompy-rpc:") for key in cache_keys)
        transfer = port.get_transfer_data()
        assert any(key.startswith("POST:/_webcompy-rpc:") for key in transfer)
        assert "rpc-root" in html_str

    @pytest.mark.asyncio
    async def test_rpc_cache_key_matches_base_url_resolution(self, tmp_path: Path) -> None:
        from webcompy.app._app import WebComPyApp
        from webcompy.app._config import WebComPyAppConfig

        build_config = _make_build_config(tmp_path)
        app = WebComPyApp(
            root_component=_make_rpc_fetch_root(),
            config=WebComPyAppConfig(base_url="/myapp/"),
        )
        app.rpc.register("add", _add)
        serving = _create_serving(app, build_config)

        await _render(app, serving)

        port = app._server_fetch_port
        assert port is not None
        cache_keys = list(port._response_cache.keys())
        assert any(key.startswith("POST:/myapp/_webcompy-rpc:") for key in cache_keys)

    @pytest.mark.asyncio
    async def test_transfer_false_skips_async_result_but_keeps_fetch_bake(self, tmp_path: Path) -> None:
        from webcompy.app._app import WebComPyApp
        from webcompy.hydration._collect import collect_transfer_data

        build_config = _make_build_config(tmp_path)
        app = WebComPyApp(root_component=_make_rpc_fetch_root_no_transfer())
        app.rpc.register("add", _add)
        serving = _create_serving(app, build_config)

        ctx = app.create_render_context("/")
        try:
            scheduler = inject(ASYNC_SCHEDULER_PORT_KEY)
            await scheduler.await_pending()
            await serving.html_generator(ctx)
            payload = collect_transfer_data(ctx._root)
        finally:
            ctx.dispose()

        assert payload.async_results == {}
        assert any(key.startswith("POST:/_webcompy-rpc:") for key in payload.fetches)


class TestErrorPropagation:
    @pytest.mark.asyncio
    async def test_rpc_error_propagates_to_client(self, tmp_path: Path) -> None:
        from webcompy.app._app import WebComPyApp

        build_config = _make_build_config(tmp_path)
        app = WebComPyApp(root_component=lambda _: None)
        app.rpc.register("boom", _boom)
        _create_serving(app, build_config)

        ctx = app.create_render_context("/")
        try:
            with pytest.raises(RpcError) as exc:
                await rpc_call("boom", result_type=int)
            assert exc.value.code == -32603
        finally:
            ctx.dispose()
