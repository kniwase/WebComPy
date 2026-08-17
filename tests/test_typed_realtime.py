from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from types import SimpleNamespace
from typing import Any
from uuid import UUID

import pytest

import webcompy.realtime._typed as typed_mod
import webcompy.realtime._ws as ws_mod
from webcompy.components import ComponentContext, define_component
from webcompy.di._scope import DIScope, _active_di_scope
from webcompy.elements import html
from webcompy.ports._keys import WEBSOCKET_PORT_KEY
from webcompy.realtime import (
    ConnectionState,
    TypedWebSocketHandle,
    WebSocketHandle,
    register_realtime_type_handler,
    use_websocket,
)
from webcompy_testing import FakeWebSocketPort, create_test_app, render_app_html


@dataclass
class ChatMessage:
    user: str
    text: str


class Color(Enum):
    RED = "red"
    BLUE = "blue"


@dataclass
class RichMessage:
    user: str
    at: datetime
    uid: UUID
    price: Decimal
    kind: Color


@dataclass
class Money:
    amount: str


@dataclass
class Payment:
    user: str
    money: Money


def _encode_money(money: Money) -> str:
    return money.amount


def _decode_money(value: Any) -> Money:
    if not isinstance(value, str):
        raise TypeError("expected money string")
    return Money(amount=value)


@pytest.fixture
def rt_env(monkeypatch):
    scope = DIScope()
    port = FakeWebSocketPort()
    scope.provide(WEBSOCKET_PORT_KEY, port)
    monkeypatch.setattr(ws_mod, "_get_app_di_scope", lambda: scope)
    monkeypatch.setattr(typed_mod, "_get_app_di_scope", lambda: scope)
    token = _active_di_scope.set(scope)
    yield SimpleNamespace(scope=scope, port=port)
    _active_di_scope.reset(token)


async def _collect(handle: Any, limit: int | None = None) -> list[Any]:
    out: list[Any] = []
    async for item in handle:
        out.append(item)
        if limit is not None and len(out) >= limit:
            break
    return out


class TestTypedIteration:
    @pytest.mark.asyncio
    async def test_valid_frames_yield_dataclass_instances(self, rt_env) -> None:
        ws = use_websocket("/ws", message_type=ChatMessage)
        assert isinstance(ws, TypedWebSocketHandle)
        rt_env.port.emit_open("/ws")
        rt_env.port.emit_message("/ws", '{"user": "ada", "text": "hi"}')
        got = await _collect(ws, limit=1)
        assert got == [ChatMessage(user="ada", text="hi")]

    @pytest.mark.asyncio
    async def test_raw_handle_unchanged_without_message_type(self, rt_env) -> None:
        ws = use_websocket("/ws")
        assert isinstance(ws, WebSocketHandle)
        assert not isinstance(ws, TypedWebSocketHandle)
        rt_env.port.emit_message("/ws", '{"user": "ada", "text": "hi"}')
        got = await _collect(ws, limit=1)
        assert got == ['{"user": "ada", "text": "hi"}']

    def test_importable_from_webcompy_and_realtime(self) -> None:
        from webcompy import TypedWebSocketHandle as root_typed
        from webcompy import register_realtime_type_handler as root_register
        from webcompy.realtime import TypedWebSocketHandle as realtime_typed
        from webcompy.realtime import register_realtime_type_handler as realtime_register

        assert root_typed is realtime_typed
        assert root_register is realtime_register


class TestTypedSend:
    @pytest.mark.asyncio
    async def test_send_emits_single_object_with_meta_member(self, rt_env) -> None:
        ws = use_websocket("/ws", message_type=ChatMessage)
        rt_env.port.emit_open("/ws")
        ws.send(ChatMessage(user="ada", text="hi"))
        assert rt_env.port.sent_frames("/ws") == ['{"user": "ada", "text": "hi", "__webcompy_transfer_meta__": {}}']

    @pytest.mark.asyncio
    async def test_metadata_fields_round_trip(self, rt_env) -> None:
        ws = use_websocket("/ws", message_type=RichMessage)
        rt_env.port.emit_open("/ws")
        sent = RichMessage(
            user="ada",
            at=datetime(2025, 1, 2, 3, 4, 5),
            uid=UUID("12345678-1234-5678-1234-567812345678"),
            price=Decimal("10.50"),
            kind=Color.RED,
        )
        ws.send(sent)
        (frame,) = rt_env.port.sent_frames("/ws")
        data = json.loads(frame)
        meta = data.pop("__webcompy_transfer_meta__")
        assert meta == {"/at": "datetime", "/uid": "uuid", "/price": "decimal"}
        rt_env.port.emit_message("/ws", json.dumps({**data, "__webcompy_transfer_meta__": meta}))
        (got,) = await _collect(ws, limit=1)
        assert got == sent


class TestSkipOnError:
    @pytest.mark.asyncio
    async def test_bad_frame_sets_last_error_and_next_valid_frame_resets_it(self, rt_env) -> None:
        ws = use_websocket("/ws", message_type=ChatMessage)
        rt_env.port.emit_open("/ws")
        errors: list[Exception | None] = []
        ws.last_error.on_after_updating(errors.append)

        async def pump() -> None:
            rt_env.port.emit_message("/ws", "not json")
            await asyncio.sleep(0)
            rt_env.port.emit_message("/ws", '{"user": "ada", "text": "hi"}')

        pump_task = asyncio.create_task(pump())
        with pytest.warns(UserWarning, match="skipping"):
            got = await _collect(ws, limit=1)
        await pump_task
        assert got == [ChatMessage(user="ada", text="hi")]
        assert len(errors) == 2
        assert errors[0] is not None
        assert errors[1] is None

    @pytest.mark.asyncio
    async def test_schema_mismatch_frame_skipped(self, rt_env) -> None:
        ws = use_websocket("/ws", message_type=ChatMessage)
        rt_env.port.emit_open("/ws")
        with pytest.warns(UserWarning, match="skipping"):
            rt_env.port.emit_message("/ws", '{"user": "ada"}')
            rt_env.port.emit_message("/ws", '{"user": "ada", "text": 42}')
            rt_env.port.emit_message("/ws", '{"user": "ada", "text": "hi"}')
            got = await _collect(ws, limit=1)
        assert got == [ChatMessage(user="ada", text="hi")]

    @pytest.mark.asyncio
    async def test_unknown_type_tag_skipped_without_resolution(self, rt_env) -> None:
        ws = use_websocket("/ws", message_type=ChatMessage)
        rt_env.port.emit_open("/ws")
        bad = '{"user": "ada", "text": "hi", "__webcompy_transfer_meta__": {"/user": "evil.module.Secret"}}'
        rt_env.port.emit_message("/ws", bad)
        task = asyncio.create_task(anext(ws))
        with pytest.warns(UserWarning, match="skipping"):
            await asyncio.sleep(0)
            assert isinstance(ws.last_error.value, ValueError)
            assert "evil.module.Secret" in str(ws.last_error.value)
            rt_env.port.emit_message("/ws", '{"user": "ada", "text": "hi"}')
            got = await task
        assert got == ChatMessage(user="ada", text="hi")
        assert ws.last_error.value is None

    @pytest.mark.asyncio
    async def test_subscription_and_shared_connection_survive_bad_frames(self, rt_env) -> None:
        raw = use_websocket("/ws")
        typed = use_websocket("/ws", message_type=ChatMessage)
        rt_env.port.emit_open("/ws")
        assert len(rt_env.port.open_calls) == 1
        with pytest.warns(UserWarning, match="skipping"):
            rt_env.port.emit_message("/ws", "not json")
            rt_env.port.emit_message("/ws", '{"user": "ada", "text": "hi"}')
            got_typed = await _collect(typed, limit=1)
            got_raw = await _collect(raw, limit=2)
        assert got_typed == [ChatMessage(user="ada", text="hi")]
        assert got_raw == ["not json", '{"user": "ada", "text": "hi"}']
        assert typed.state.value is ConnectionState.OPEN
        assert raw.state.value is ConnectionState.OPEN


class TestStrictness:
    @pytest.mark.asyncio
    async def test_extra_field_skipped_in_strict_mode(self, rt_env) -> None:
        ws = use_websocket("/ws", message_type=ChatMessage)
        rt_env.port.emit_open("/ws")
        with pytest.warns(UserWarning, match="skipping"):
            rt_env.port.emit_message("/ws", '{"user": "ada", "text": "hi", "admin": true}')
            rt_env.port.emit_message("/ws", '{"user": "ada", "text": "hi"}')
            got = await _collect(ws, limit=1)
        assert got == [ChatMessage(user="ada", text="hi")]

    @pytest.mark.asyncio
    async def test_lenient_mode_yields_extra_field_frame(self, rt_env) -> None:
        ws = use_websocket("/ws", message_type=ChatMessage, strict=False)
        rt_env.port.emit_open("/ws")
        rt_env.port.emit_message("/ws", '{"user": "ada", "text": "hi", "admin": true}')
        got = await _collect(ws, limit=1)
        assert got == [ChatMessage(user="ada", text="hi")]

    @pytest.mark.asyncio
    async def test_missing_field_skipped_in_strict_mode(self, rt_env) -> None:
        ws = use_websocket("/ws", message_type=ChatMessage)
        rt_env.port.emit_open("/ws")
        with pytest.warns(UserWarning, match="skipping"):
            rt_env.port.emit_message("/ws", '{"user": "ada"}')
            rt_env.port.emit_message("/ws", '{"user": "ada", "text": "hi"}')
            got = await _collect(ws, limit=1)
        assert got == [ChatMessage(user="ada", text="hi")]


class TestAllowlist:
    @pytest.mark.asyncio
    async def test_custom_type_round_trip(self, rt_env) -> None:
        register_realtime_type_handler(Money, _encode_money, _decode_money)
        ws = use_websocket("/ws", message_type=Payment)
        rt_env.port.emit_open("/ws")
        sent = Payment(user="ada", money=Money(amount="10"))
        ws.send(sent)
        (frame,) = rt_env.port.sent_frames("/ws")
        data = json.loads(frame)
        assert set(data["__webcompy_transfer_meta__"]) == {"/money"}
        rt_env.port.emit_message("/ws", frame)
        (got,) = await _collect(ws, limit=1)
        assert got == sent

    @pytest.mark.asyncio
    async def test_unregistered_custom_tag_skipped(self, rt_env) -> None:
        ws = use_websocket("/ws", message_type=Payment)
        rt_env.port.emit_open("/ws")
        bad = '{"user": "ada", "money": "10", "__webcompy_transfer_meta__": {"/money": "tests.test_typed_realtime.Money"}}'
        rt_env.port.emit_message("/ws", bad)
        task = asyncio.create_task(anext(ws))
        with pytest.warns(UserWarning, match="skipping"):
            await asyncio.sleep(0)
            assert ws.last_error.value is not None
            assert "tests.test_typed_realtime.Money" in str(ws.last_error.value)
            rt_env.port.emit_message("/ws", bad)
            rt_env.port.emit_message(
                "/ws", '{"user": "ada", "money": "10", "__webcompy_transfer_meta__": {"/money": "unknown.Type"}}'
            )
            rt_env.port.emit_message("/ws", '{"user": "ada", "money": "10"}')
            rt_env.port.emit_message("/ws", '{"user": "ada", "money": {"amount": "10"}}')
            got = await task
        assert got == Payment(user="ada", money=Money(amount="10"))
        assert ws.last_error.value is None

    def test_registration_outside_di_scope_warns_and_is_noop(self, monkeypatch) -> None:
        monkeypatch.setattr(typed_mod, "_get_app_di_scope", lambda: None)
        with pytest.warns(UserWarning, match="no app DI scope"):
            register_realtime_type_handler(Money, _encode_money, _decode_money)
        scope = DIScope()
        assert scope.inject(typed_mod._REALTIME_TYPE_REGISTRY_KEY, default=None) is None


class TestNonDataclassTarget:
    def test_list_target_rejected(self) -> None:
        with pytest.raises(TypeError, match="dataclass"):
            use_websocket("/ws", message_type=list[int])

    def test_scalar_target_rejected(self) -> None:
        with pytest.raises(TypeError, match="dataclass"):
            use_websocket("/ws", message_type=str)


class TestSsr:
    def test_ssr_typed_handle_falls_back_like_raw(self, monkeypatch) -> None:
        from webcompy_server.ports import ServerWebSocketPort

        scope = DIScope()
        scope.provide(WEBSOCKET_PORT_KEY, ServerWebSocketPort())
        monkeypatch.setattr(ws_mod, "_get_app_di_scope", lambda: scope)
        monkeypatch.setattr(typed_mod, "_get_app_di_scope", lambda: scope)
        token = _active_di_scope.set(scope)
        try:
            with pytest.warns(UserWarning, match="outside the browser"):
                ws = use_websocket("/ws", message_type=ChatMessage)
            assert ws.state.value is ConnectionState.CLOSED
            assert ws.last_error.value is None
            got = asyncio.run(_collect(ws))
            assert got == []
            with pytest.warns(UserWarning, match="closed"):
                ws.send(ChatMessage(user="ada", text="hi"))
        finally:
            _active_di_scope.reset(token)

    def test_ssr_render_payload_contains_no_typed_realtime_entries(self) -> None:
        with pytest.warns(UserWarning, match="no app DI scope"):
            register_realtime_type_handler(Money, _encode_money, _decode_money)

        @define_component("typed-ssr-comp")
        def TypedSsrComp(context: ComponentContext[None]):
            ws = use_websocket("/ws", message_type=ChatMessage)
            return html.SPAN({}, ws.state.value.name)

        app = create_test_app(root_component=TypedSsrComp)
        with pytest.warns(UserWarning, match="outside the browser"):
            html_out = render_app_html(
                app,
                app_package_name="test_pkg",
                dev_mode=False,
                prerender=True,
                wheel_filename="test_pkg-0+sha.abcdef12-py3-none-any.whl",
            )
        assert "ChatMessage" not in html_out
        assert "webcompy-realtime" not in html_out
        assert "transfer_meta" not in html_out
