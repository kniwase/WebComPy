from __future__ import annotations

import asyncio
import html
import json
import re

import pytest

from webcompy.components._generator import define_component
from webcompy.di._keys import RPC_REGISTRY_KEY
from webcompy.di._scope import DIScope, _active_di_scope
from webcompy.ports._keys import WEBSOCKET_PORT_KEY
from webcompy.realtime import ConnectionState
from webcompy.rpc import RpcError, RpcSubscriptionState, RpcWsClient
from webcompy.rpc._registry import ProcedureRegistry
from webcompy_server.ports import ServerWebSocketPort
from webcompy_testing import create_test_app, render_app_html

_WEBCOMPY_DATA_RE = re.compile(r'<script type="application/json" id="__webcompy_data__">(.*?)</script>', re.DOTALL)


@define_component("rpc-ws-ssr-root")
def RpcWsSsrRoot(context):
    from webcompy.elements import html

    RpcWsClient()
    return html.DIV({"data-testid": "ssr"}, "ssr")


def _render() -> str:
    app = create_test_app(root_component=RpcWsSsrRoot)
    return render_app_html(
        app,
        app_package_name="test_pkg",
        dev_mode=False,
        prerender=True,
        wheel_filename="test_pkg-0+sha.abcdef12-py3-none-any.whl",
    )


class TestSsrNoOp:
    def test_construction_warns_and_performs_no_socket_work(self) -> None:
        rendered = _render()
        # no websocket is opened and no RPC-WS state is transferred
        assert '"websocket"' not in rendered

    def test_render_transfer_payload_has_no_rpc_ws_state(self) -> None:
        rendered = _render()
        match = _WEBCOMPY_DATA_RE.search(rendered)
        assert match is not None
        payload = json.loads(html.unescape(match.group(1)))
        assert payload["signals"] == {}
        assert "subscription" not in json.dumps(payload)
        assert "cursor" not in json.dumps(payload)

    def test_ssr_client_is_inert(self) -> None:
        scope = DIScope()
        scope.provide(RPC_REGISTRY_KEY, ProcedureRegistry())
        scope.provide(WEBSOCKET_PORT_KEY, ServerWebSocketPort())
        token = _active_di_scope.set(scope)
        try:
            with pytest.warns(UserWarning, match="outside the browser"):
                client = RpcWsClient()
            assert client.state.value == ConnectionState.CLOSED
            with pytest.raises(RpcError):
                asyncio.run(client.call("add", {"a": 1}))
            with pytest.raises(RpcError):
                asyncio.run(client.notify("record"))
            sub = client.subscribe("ticker", {}, event_type=dict)
            assert sub.state.value == RpcSubscriptionState.CLOSED
            with pytest.raises(StopAsyncIteration):
                asyncio.run(sub.__anext__())
        finally:
            _active_di_scope.reset(token)

    def test_ssr_client_without_registry_raises(self) -> None:
        scope = DIScope()
        scope.provide(WEBSOCKET_PORT_KEY, ServerWebSocketPort())
        token = _active_di_scope.set(scope)
        try:
            with pytest.raises(RpcError, match="registry is not available"):
                RpcWsClient()
        finally:
            _active_di_scope.reset(token)
