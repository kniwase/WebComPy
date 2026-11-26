from __future__ import annotations

import logging
from unittest.mock import MagicMock

import pytest

from tests.test_hydration_preservation_helpers import make_prerendered_parent
from webcompy.components._component import _active_app_context
from webcompy.elements.types._element import Element
from webcompy.hydration import HydrationMismatchRecord, record_mismatch
from webcompy.hydration._report import HydrationReporter, emit_report_summary
from webcompy_testing import FakeDOMNode


class _FakeCtx:
    def __init__(self) -> None:
        self._hydration_in_progress: bool = True
        self._hydration_reporter = HydrationReporter()


@pytest.fixture
def hydration_window():
    ctx = _FakeCtx()
    token = _active_app_context.set(ctx)
    yield ctx
    _active_app_context.reset(token)


def test_record_captures_only_within_hydration_window(hydration_window):
    record_mismatch("tag", "div", "span", "my-comp")
    hydration_window._hydration_in_progress = False
    record_mismatch("text", "expected", "actual")

    assert len(hydration_window._hydration_reporter.records) == 1
    record = hydration_window._hydration_reporter.records[0]
    assert record.kind == "tag"
    assert record.expected == "div"
    assert record.actual == "span"
    assert record.component_id == "my-comp"


def test_record_is_noop_without_active_context():
    record_mismatch("attribute", "x", "y", "")
    # no exception and no global side effects
    assert True


def test_records_are_frozen_dataclasses():
    rec = HydrationMismatchRecord("node-count", 3, 5, "list")
    assert rec.kind == "node-count"
    assert rec.expected == 3
    assert rec.actual == 5
    assert rec.component_id == "list"


def test_emit_report_summary_logs_single_aggregated_warning(hydration_window, monkeypatch, caplog):
    captured: list[tuple[object, ...]] = []
    monkeypatch.setattr("webcompy.logging.warn", lambda *args: captured.append(args))

    record_mismatch("tag", "div", "span", "comp-a")
    record_mismatch("tag", "p", "div", "comp-a")
    record_mismatch("text", "a", "b", "comp-b")

    with caplog.at_level(logging.WARNING, logger="webcompy.hydration"):
        emit_report_summary(hydration_window)

    assert caplog.records == []
    assert len(captured) == 1
    text = str(captured[0][0])
    assert "Hydration mismatches detected (3)" in text
    assert "tag=2" in text
    assert "text=1" in text
    assert "comp-a(2)" in text
    assert "comp-b(1)" in text


def test_emit_report_summary_silent_when_no_records(hydration_window, monkeypatch, caplog):
    captured: list[tuple[object, ...]] = []
    monkeypatch.setattr("webcompy.logging.warn", lambda *args: captured.append(args))

    with caplog.at_level(logging.WARNING, logger="webcompy.hydration"):
        emit_report_summary(hydration_window)

    assert caplog.records == []
    assert captured == []


def test_render_context_exposes_hydration_report():
    from webcompy.app._render_context import RenderContext

    assert isinstance(RenderContext.hydration_report, property)


def test_excess_prerendered_nodes_yield_single_node_count_record(hydration_window):
    prerendered = FakeDOMNode("div")
    prerendered.__webcompy_prerendered_node__ = True
    for _ in range(3):
        child = FakeDOMNode("div")
        child.__webcompy_prerendered_node__ = True
        prerendered.appendChild(child)
    parent = make_prerendered_parent(prerendered)
    el = Element("div", {}, {}, None, [])
    el._parent = parent
    el._node_idx = 0
    parent._children = [el]

    el._hydrate_node()

    records = [r for r in hydration_window._hydration_reporter.records if r.kind == "node-count"]
    assert len(records) == 1
    assert records[0].expected == 0
    assert records[0].actual == 3


class TestHydrationWindowClose:
    @staticmethod
    def _make_root(monkeypatch, ctx, *, on_after=None):
        from webcompy.app import _root_component as rc
        from webcompy.app._root_component import AppDocumentRoot
        from webcompy.di._keys import _ROUTER_KEY
        from webcompy.di._scope import DIScope
        from webcompy.ports._keys import (
            ASYNC_SCHEDULER_PORT_KEY,
            DOM_PORT_KEY,
            FFI_PORT_KEY,
            HOST_PORT_KEY,
        )
        from webcompy_testing import FakeAsyncSchedulerPort

        monkeypatch.setattr(rc, "ENVIRONMENT", "pyscript")

        scope = DIScope()
        scope.provide(DOM_PORT_KEY, MagicMock(query_selector=lambda *a, **k: None))
        scope.provide(FFI_PORT_KEY, MagicMock())
        scope.provide(HOST_PORT_KEY, MagicMock())
        scheduler = FakeAsyncSchedulerPort()
        scope.provide(ASYNC_SCHEDULER_PORT_KEY, scheduler)
        scope.provide(_ROUTER_KEY, None)

        root = AppDocumentRoot.__new__(AppDocumentRoot)
        root._di_scope = scope
        root._app = MagicMock(_hydrate=True)
        root._AppDocumentRoot__hydrated = False
        root._AppDocumentRoot__loading = True
        root._children = []
        root._router = None
        root._selector = None
        root._property = {
            "on_before_rendering": lambda: None,
            "on_after_rendering": on_after or (lambda: None),
        }
        root._head_element = MagicMock()
        root._head_element._render = _noop_async
        return root

    @pytest.mark.asyncio
    async def test_window_closed_after_successful_render(self, monkeypatch):
        ctx = _FakeCtx()
        ctx._hydration_in_progress = False
        token = _active_app_context.set(ctx)
        try:
            root = self._make_root(monkeypatch, ctx)
            await root._render()
            assert ctx._hydration_in_progress is False
        finally:
            _active_app_context.reset(token)

    @pytest.mark.asyncio
    async def test_window_closed_when_root_render_raises(self, monkeypatch):
        ctx = _FakeCtx()
        token = _active_app_context.set(ctx)
        try:

            def _boom():
                raise RuntimeError("render failed")

            root = self._make_root(monkeypatch, ctx, on_after=_boom)
            with pytest.raises(RuntimeError, match="render failed"):
                await root._render()
            assert ctx._hydration_in_progress is False
            assert getattr(ctx, "_hydration_payload_closed", False) is True
        finally:
            _active_app_context.reset(token)

    @pytest.mark.asyncio
    async def test_summary_emitted_after_window_closed(self, monkeypatch):
        from webcompy.app import _root_component as rc

        ctx = _FakeCtx()
        token = _active_app_context.set(ctx)
        try:
            captured = {}
            original = rc.emit_report_summary

            def _spy(inner_ctx):
                captured["window_open"] = bool(getattr(inner_ctx, "_hydration_in_progress", False))
                return original(inner_ctx)

            monkeypatch.setattr(rc, "emit_report_summary", _spy)
            root = self._make_root(monkeypatch, ctx)
            await root._render()

            assert captured["window_open"] is False
            assert ctx._hydration_in_progress is False
        finally:
            _active_app_context.reset(token)

    @pytest.mark.asyncio
    async def test_payload_closed_before_loading_fade(self, monkeypatch):
        from webcompy.ports._keys import DOM_PORT_KEY

        ctx = _FakeCtx()
        token = _active_app_context.set(ctx)
        try:
            observed: dict[str, bool] = {}

            def _query_selector(*args, **kwargs):
                observed["payload_closed_at_fade"] = bool(getattr(ctx, "_hydration_payload_closed", False))
                return None

            root = self._make_root(monkeypatch, ctx)
            root._di_scope.provide(
                DOM_PORT_KEY,
                lambda: MagicMock(query_selector=_query_selector, get_element_by_id=lambda *a, **k: None),
            )
            await root._render()

            assert observed["payload_closed_at_fade"] is True
            assert getattr(ctx, "_hydration_payload_closed", False) is True
        finally:
            _active_app_context.reset(token)

    @pytest.mark.asyncio
    async def test_records_after_render_are_not_captured(self, monkeypatch):
        ctx = _FakeCtx()
        token = _active_app_context.set(ctx)
        try:
            root = self._make_root(monkeypatch, ctx)
            await root._render()

            record_mismatch("text", "a", "b")
            assert ctx._hydration_reporter.records == []
        finally:
            _active_app_context.reset(token)

    @pytest.mark.asyncio
    async def test_deferred_cookie_theme_applied_after_window_closes_without_mismatch(self, monkeypatch):
        from webcompy.ports._keys import COOKIE_PORT_KEY
        from webcompy.ui.theme._manager import ThemeManager
        from webcompy.ui.theme._theme import THEME_KEY, Theme

        ctx = _FakeCtx()
        cookie_writes: list[tuple[str, str]] = []

        class _CookieSpy:
            def set(self, name: str, value: str, **kwargs: object) -> None:
                cookie_writes.append((name, value))

            def delete(self, name: str, **kwargs: object) -> None:
                cookie_writes.append((name, ""))

        root = self._make_root(monkeypatch, ctx)
        ctx.di_scope = root._di_scope
        manager = ThemeManager(root._app, ctx, Theme.SYSTEM)
        root._di_scope.provide(THEME_KEY, manager)
        root._di_scope.provide(COOKIE_PORT_KEY, _CookieSpy())
        ctx._deferred_theme = Theme.DARK

        token = _active_app_context.set(ctx)
        try:
            await root._render()
        finally:
            _active_app_context.reset(token)

        assert ctx._hydration_reporter.records == []
        assert ctx._deferred_theme is None
        assert manager.value is Theme.DARK
        assert cookie_writes == []


async def _noop_async():
    return None
