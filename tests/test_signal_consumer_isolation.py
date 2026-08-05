from __future__ import annotations

from types import SimpleNamespace

from webcompy.components._component import _active_app_context, _set_app_instance
from webcompy.signal import Computed, Signal
from webcompy.signal._graph import _get_in_notification_phase


def _use_fake_app(fake_ctx):
    token = _active_app_context.set(None)
    _set_app_instance(fake_ctx)
    return token


def _release_fake_app(token):
    _set_app_instance(None)
    _active_app_context.reset(token)


class TestConsumerIsolation:
    def test_failing_consumer_does_not_block_siblings(self):
        received_errors: list[Exception] = []
        received_b: list[int] = []
        received_c: list[int] = []
        fake_ctx = SimpleNamespace(_config=SimpleNamespace(on_error=received_errors.append))

        def bad(value: int):
            raise RuntimeError("consumer boom")

        signal = Signal(0)
        signal.on_after_updating(bad)
        signal.on_after_updating(lambda v: received_b.append(v))
        signal.on_after_updating(lambda v: received_c.append(v))

        token = _use_fake_app(fake_ctx)
        try:
            signal.value = 1
        finally:
            _release_fake_app(token)

        assert received_b == [1]
        assert received_c == [1]
        assert len(received_errors) == 1
        assert str(received_errors[0]) == "consumer boom"

    def test_producer_value_consistent_after_consumer_raises(self):
        fake_ctx = SimpleNamespace(_config=SimpleNamespace(on_error=lambda e: None))
        signal = Signal("old")

        def bad(value: str):
            raise RuntimeError("boom")

        signal.on_after_updating(bad)

        token = _use_fake_app(fake_ctx)
        try:
            signal.value = "new"
        finally:
            _release_fake_app(token)

        assert signal.value == "new"

    def test_sibling_computed_not_stuck_dirty(self):
        fake_ctx = SimpleNamespace(_config=SimpleNamespace(on_error=lambda e: None))
        signal = Signal(1)
        doubled = Computed(lambda: signal.value * 2)

        def bad(value: int):
            raise RuntimeError("boom")

        signal.on_after_updating(bad)
        assert doubled.value == 2

        token = _use_fake_app(fake_ctx)
        try:
            signal.value = 5
        finally:
            _release_fake_app(token)

        assert doubled.value == 10
        assert signal.value == 5

    def test_notification_phase_restored_after_consumer_raises(self):
        fake_ctx = SimpleNamespace(_config=SimpleNamespace(on_error=lambda e: None))
        signal = Signal(0)

        def bad(value: int):
            raise RuntimeError("boom")

        signal.on_after_updating(bad)

        token = _use_fake_app(fake_ctx)
        try:
            signal.value = 1
        finally:
            _release_fake_app(token)

        assert _get_in_notification_phase() is False

    def test_async_consumer_error_routed_to_pipeline(self):
        received: list[Exception] = []
        fake_ctx = SimpleNamespace(_config=SimpleNamespace(on_error=received.append))
        signal = Signal(0)

        async def bad(value: int):
            raise RuntimeError("async consumer boom")

        signal.on_after_updating(bad)

        token = _use_fake_app(fake_ctx)
        try:
            signal.value = 1
        finally:
            _release_fake_app(token)

        assert len(received) == 1
        assert str(received[0]) == "async consumer boom"

    def test_default_logging_without_handler(self, monkeypatch):
        logged: list[Exception] = []
        monkeypatch.setattr("webcompy.aio._aio._log_error", lambda e: logged.append(e))
        signal = Signal(0)

        def bad(value: int):
            raise RuntimeError("logged boom")

        signal.on_after_updating(bad)

        token = _active_app_context.set(None)
        _set_app_instance(None)
        try:
            signal.value = 1
        finally:
            _active_app_context.reset(token)

        assert len(logged) == 1
