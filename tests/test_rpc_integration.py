from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import patch

import pytest

from webcompy.di import inject
from webcompy.ports._keys import ASYNC_SCHEDULER_PORT_KEY
from webcompy.rpc import Procedure, RpcHttpClient, batch, notify
from webcompy.rpc._errors import RpcError
from webcompy_cli._build import BuildArtifacts
from webcompy_cli.config._build_config import WebComPyBuildConfig


@dataclass
class AddParams:
    a: int
    b: int = 0


@dataclass
class BoomParams:
    pass


add = Procedure("add", AddParams, int)
boom = Procedure("boom", BoomParams, int)


def _add_impl(p: AddParams) -> int:
    return p.a + p.b


def _boom_impl(p: BoomParams) -> int:
    raise RuntimeError("boom")


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
        client = RpcHttpClient()
        result = use_async_result(lambda: add(client, AddParams(a=1, b=2)))
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
        client = RpcHttpClient()
        result = use_async_result(lambda: add(client, AddParams(a=1, b=2)), transfer=False)
        return html.DIV(
            {"data-testid": "rpc-root-no-transfer"},
            str(result.data.value) if result.data.value is not None else "",
        )

    return RpcFetchRootNoTransfer


def _make_rpc_notify_root():
    from webcompy.components import define_component
    from webcompy.components._hooks import use_async_result
    from webcompy.elements import html

    @define_component("rpc-notify-root")
    def RpcNotifyRoot(context):
        client = RpcHttpClient()

        async def _fire() -> None:
            await notify(add(client, AddParams(a=1)))

        use_async_result(_fire)
        return html.DIV({"data-testid": "rpc-notify-root"}, "")

    return RpcNotifyRoot


def _make_rpc_batch_root():
    from webcompy.components import define_component
    from webcompy.components._hooks import use_async_result
    from webcompy.elements import html

    @define_component("rpc-batch-root")
    def RpcBatchRoot(context):
        client = RpcHttpClient()
        result = use_async_result(lambda: batch(add(client, AddParams(a=1)), add(client, AddParams(a=2))))
        total = sum(result.data.value) if result.data.value is not None else ""
        return html.DIV({"data-testid": "rpc-batch-root"}, str(total))

    return RpcBatchRoot


async def _render(app, serving) -> str:
    ctx = app.create_render_context("/")
    try:
        scheduler = inject(ASYNC_SCHEDULER_PORT_KEY)
        await scheduler.await_pending()
        return await serving.html_generator(ctx)
    finally:
        ctx.dispose()


def _render_with_ctx_port(app, serving):
    from webcompy.ports._keys import FETCH_PORT_KEY

    async def _go() -> tuple[str, object]:
        ctx = app.create_render_context("/")
        try:
            ctx_port = ctx.di_scope.inject(FETCH_PORT_KEY)
            scheduler = inject(ASYNC_SCHEDULER_PORT_KEY)
            await scheduler.await_pending()
            html_str = await serving.html_generator(ctx)
            return html_str, ctx_port
        finally:
            ctx.dispose()

    return _go()


class TestSsrBake:
    @pytest.mark.asyncio
    async def test_rpc_during_ssr_is_baked(self, tmp_path: Path) -> None:
        from webcompy.app._app import WebComPyApp

        build_config = _make_build_config(tmp_path)
        app = WebComPyApp(root_component=_make_rpc_fetch_root())
        app.rpc.bind(add, _add_impl)
        serving = _create_serving(app, build_config)

        html_str, port = await _render_with_ctx_port(app, serving)
        cache_keys = list(port._response_cache.keys())
        assert any(key.startswith("POST:/_webcompy-rpc:") for key in cache_keys)
        transfer = port.get_transfer_data()
        assert any(key.startswith("POST:/_webcompy-rpc:") for key in transfer)
        assert "rpc-root" in html_str
        assert "3" in html_str

    @pytest.mark.asyncio
    async def test_batch_during_ssr_is_baked_as_single_array_entry(self, tmp_path: Path) -> None:
        from webcompy.app._app import WebComPyApp

        build_config = _make_build_config(tmp_path)
        app = WebComPyApp(root_component=_make_rpc_batch_root())
        app.rpc.bind(add, _add_impl)
        serving = _create_serving(app, build_config)

        html_str, port = await _render_with_ctx_port(app, serving)
        transfer = port.get_transfer_data()
        batch_keys = [key for key in transfer if key.startswith("POST:/_webcompy-rpc:[")]
        assert len(batch_keys) == 1, f"expected exactly one baked array entry, got {list(transfer)}"
        body = json.loads(transfer[batch_keys[0]].body)
        assert isinstance(body, list)
        assert len(body) == 2
        # the baked entry is the cached batch response array
        assert all(entry.get("jsonrpc") == "2.0" and "result" in entry for entry in body)
        assert sorted(entry["result"] for entry in body) == [1, 2]
        assert "rpc-batch-root" in html_str
        assert "3" in html_str

    @pytest.mark.asyncio
    async def test_notify_during_ssr_is_not_baked(self, tmp_path: Path) -> None:
        from webcompy.app._app import WebComPyApp

        build_config = _make_build_config(tmp_path)
        app = WebComPyApp(root_component=_make_rpc_notify_root())
        app.rpc.bind(add, _add_impl)
        serving = _create_serving(app, build_config)

        html_str, port = await _render_with_ctx_port(app, serving)
        transfer = port.get_transfer_data()
        rpc_keys = [key for key in transfer if key.startswith("POST:/_webcompy-rpc")]
        assert rpc_keys == [], f"notify during SSR must not be baked, got {rpc_keys}"
        assert "rpc-notify-root" in html_str

    @pytest.mark.asyncio
    async def test_rpc_cache_key_matches_base_url_resolution(self, tmp_path: Path) -> None:
        from webcompy.app._app import WebComPyApp
        from webcompy.app._config import WebComPyAppConfig

        build_config = _make_build_config(tmp_path)
        app = WebComPyApp(
            root_component=_make_rpc_fetch_root(),
            config=WebComPyAppConfig(base_url="/myapp/"),
        )
        app.rpc.bind(add, _add_impl)
        serving = _create_serving(app, build_config)

        _html_str, port = await _render_with_ctx_port(app, serving)
        cache_keys = list(port._response_cache.keys())
        assert any(key.startswith("POST:/myapp/_webcompy-rpc:") for key in cache_keys)

    @pytest.mark.asyncio
    async def test_transfer_false_skips_async_result_but_keeps_fetch_bake(self, tmp_path: Path) -> None:
        from webcompy.app._app import WebComPyApp
        from webcompy.hydration._collect import collect_transfer_data

        build_config = _make_build_config(tmp_path)
        app = WebComPyApp(root_component=_make_rpc_fetch_root_no_transfer())
        app.rpc.bind(add, _add_impl)
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
        app.rpc.bind(boom, _boom_impl)
        _create_serving(app, build_config)

        ctx = app.create_render_context("/")
        try:
            client = RpcHttpClient()
            with pytest.raises(RpcError) as exc:
                await boom(client, BoomParams())
            assert exc.value.code == -32603
        finally:
            ctx.dispose()


def test_integration_contract_call_via_fetch():
    from webcompy.di import DIScope, provide
    from webcompy.di._keys import RPC_REGISTRY_KEY as _RPC_REGISTRY_KEY
    from webcompy.ports._fetch import Response
    from webcompy.ports._keys import FETCH_PORT_KEY as _FETCH_PORT_KEY
    from webcompy.rpc._registry import ProcedureRegistry as _ProcedureRegistry

    registry = _ProcedureRegistry()
    registry.bind(add, _add_impl)

    class FakeFetch:
        async def fetch(self, url, method="POST", headers=None, body=None):
            payload = json.loads(body)

            from webcompy_server.rpc._dispatcher import dispatch_payload

            result = await dispatch_payload(payload, registry)
            return Response(text=json.dumps(result), headers={}, status_code=200, status_text="OK", ok=True)

    scope = DIScope()
    scope.__enter__()
    try:
        provide(_FETCH_PORT_KEY, FakeFetch())
        provide(_RPC_REGISTRY_KEY, registry)
        client = RpcHttpClient()
        import asyncio

        async def _run():
            return await add(client, AddParams(a=1, b=2))

        result = asyncio.run(_run())
        assert result == 3
    finally:
        scope.__exit__(None, None, None)
