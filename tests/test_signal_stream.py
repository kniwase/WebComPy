from __future__ import annotations

import asyncio

import pytest

from webcompy.aio import (
    StreamListResult,
    StreamResult,
    to_async_iter,
    to_reactive_list,
    to_signal,
)
from webcompy.components._hooks import _active_component_context, on_before_destroy
from webcompy.components._libs import Context
from webcompy.signal import Signal


def _make_context() -> Context:
    return Context(
        props=None,
        slots={},
        component_name="StreamComp",
        title_getter=lambda: "",
        meta_getter=lambda: {},
        title_setter=lambda x: None,
        meta_setter=lambda k, v: None,
    )


async def _counting() -> int:
    n = 0
    while True:
        n += 1
        yield n
        await asyncio.sleep(0.001)


class TestToSignal:
    @pytest.mark.asyncio
    async def test_returns_stream_result_shape(self):
        result = to_signal(_counting(), 42)
        assert isinstance(result, StreamResult)
        assert result.value.value == 42
        assert result.error.value is None
        assert result.finished.value is False
        result.aclose()
        await asyncio.sleep(0.02)

    @pytest.mark.asyncio
    async def test_bridges_async_generator_with_per_item_updates(self):
        async def gen():
            yield 1
            yield 2
            yield 3

        updates = []
        result = to_signal(gen(), 0)
        result.value.on_after_updating(lambda v: updates.append(v))
        assert result.value.value == 0
        await asyncio.sleep(0.05)
        assert updates == [1, 2, 3]
        assert result.value.value == 3
        assert result.finished.value is True
        assert result.error.value is None

    @pytest.mark.asyncio
    async def test_equal_consecutive_items_are_not_re_notified(self):
        async def gen():
            yield 1
            yield 1
            yield 2

        updates = []
        result = to_signal(gen(), 0)
        result.value.on_after_updating(lambda v: updates.append(v))
        await asyncio.sleep(0.05)
        assert updates == [1, 2]
        assert result.value.value == 2

    @pytest.mark.asyncio
    async def test_exhaustion_marks_finished(self):
        result = to_signal(_three_items(), 0)
        await asyncio.sleep(0.05)
        assert result.finished.value is True
        assert result.error.value is None

    @pytest.mark.asyncio
    async def test_plain_sync_iterable_is_accepted(self):
        result = to_signal([10, 20, 30], 0)
        await asyncio.sleep(0.05)
        assert result.value.value == 30
        assert result.finished.value is True
        assert result.error.value is None

    @pytest.mark.asyncio
    async def test_source_error_lands_on_error_signal(self):
        async def gen():
            yield 1
            raise ValueError("boom")

        result = to_signal(gen(), 0)
        await asyncio.sleep(0.05)
        assert result.value.value == 1
        assert isinstance(result.error.value, ValueError)
        assert result.error.value.args == ("boom",)
        assert result.finished.value is True

    @pytest.mark.asyncio
    async def test_aclose_stops_pump_silently(self):
        async def gen():
            yield 1
            await asyncio.sleep(0.05)

        result = to_signal(gen(), 0)
        await asyncio.sleep(0.01)
        assert result.value.value == 1
        result.aclose()
        await asyncio.sleep(0.1)
        assert result.error.value is None
        assert result.finished.value is False


class TestToReactiveList:
    @pytest.mark.asyncio
    async def test_accumulates_with_occurrence_semantics(self):
        result = to_reactive_list(_three_items())
        assert isinstance(result, StreamListResult)
        await asyncio.sleep(0.05)
        assert list(result.items) == ["a", "b", "b"]
        assert result.finished.value is True
        assert result.error.value is None

    @pytest.mark.asyncio
    async def test_maxlen_keeps_newest_items(self):
        result = to_reactive_list(_three_numbers(), maxlen=2)
        await asyncio.sleep(0.05)
        assert list(result.items) == [2, 3]

    @pytest.mark.asyncio
    async def test_unbounded_default(self):
        result = to_reactive_list(range(5))
        await asyncio.sleep(0.05)
        assert list(result.items) == [0, 1, 2, 3, 4]
        assert result.finished.value is True

    @pytest.mark.asyncio
    async def test_source_error_matches_to_signal_model(self):
        async def gen():
            yield 1
            raise RuntimeError("fail")

        result = to_reactive_list(gen())
        await asyncio.sleep(0.05)
        assert list(result.items) == [1]
        assert isinstance(result.error.value, RuntimeError)
        assert result.finished.value is True


class TestToAsyncIter:
    @pytest.mark.asyncio
    async def test_delivers_updates_in_order(self):
        sig = Signal(0)
        collected: list[int] = []

        async def collect():
            async for v in to_async_iter(sig):
                collected.append(v)
                if len(collected) >= 2:
                    break

        task = asyncio.ensure_future(collect())
        await asyncio.sleep(0)
        sig.value = 1
        await asyncio.sleep(0)
        sig.value = 2
        await task
        assert collected == [1, 2]

    @pytest.mark.asyncio
    async def test_equal_consecutive_writes_produce_no_item(self):
        sig = Signal(0)
        collected: list[int] = []

        async def collect():
            async for v in to_async_iter(sig):
                collected.append(v)
                if len(collected) >= 2:
                    break

        task = asyncio.ensure_future(collect())
        await asyncio.sleep(0)
        sig.value = 1
        sig.value = 1
        sig.value = 2
        await task
        assert collected == [1, 2]

    @pytest.mark.asyncio
    async def test_emit_initial_delivers_current_value_first(self):
        sig = Signal(5)
        collected: list[int] = []

        async def collect():
            async for v in to_async_iter(sig, emit_initial=True):
                collected.append(v)
                break

        task = asyncio.ensure_future(collect())
        await asyncio.sleep(0.01)
        await task
        assert collected == [5]

    @pytest.mark.asyncio
    async def test_no_emit_initial_by_default(self):
        sig = Signal(5)
        collected: list[int] = []

        async def collect():
            async for v in to_async_iter(sig):
                collected.append(v)
                break

        task = asyncio.ensure_future(collect())
        await asyncio.sleep(0)
        sig.value = 7
        await task
        assert collected == [7]

    @pytest.mark.asyncio
    async def test_slow_consumer_maxlen_drops_oldest(self):
        sig = Signal(0)
        collected: list[int] = []

        async def collect():
            async for v in to_async_iter(sig, maxlen=2):
                collected.append(v)
                if len(collected) >= 2:
                    break

        task = asyncio.ensure_future(collect())
        await asyncio.sleep(0)
        sig.value = 1
        sig.value = 2
        sig.value = 3
        await task
        assert collected == [2, 3]

    @pytest.mark.asyncio
    async def test_subscription_removed_after_async_for_abandonment(self):
        sig = Signal(0)
        collected: list[int] = []

        async def collect():
            async for v in to_async_iter(sig):
                collected.append(v)
                break

        task = asyncio.ensure_future(collect())
        await asyncio.sleep(0)
        sig.value = 1
        await task
        assert collected == [1]
        assert sig.consumers is None
        sig.value = 2
        await asyncio.sleep(0.01)
        assert collected == [1]


class TestLifecycle:
    @pytest.mark.asyncio
    async def test_component_destroy_cancels_pump(self):
        ctx = _make_context()
        token = _active_component_context.set(ctx)
        try:
            result = to_signal(_counting(), 0)
        finally:
            _active_component_context.reset(token)

        hooks = ctx.__get_lifecyclehooks__()
        assert "on_before_destroy" in hooks
        await asyncio.sleep(0.01)
        assert result.value.value > 0

        hooks["on_before_destroy"]()
        last = result.value.value
        await asyncio.sleep(0.02)
        assert result.value.value == last
        assert result.error.value is None
        assert result.finished.value is False

    @pytest.mark.asyncio
    async def test_cleanup_chains_with_existing_hook(self):
        ctx = _make_context()
        order: list[str] = []
        token = _active_component_context.set(ctx)
        try:

            @on_before_destroy
            def _user_hook():
                order.append("user")

            result = to_signal(_counting(), 0)
        finally:
            _active_component_context.reset(token)

        hooks = ctx.__get_lifecyclehooks__()
        hooks["on_before_destroy"]()
        assert "user" in order
        last = result.value.value
        await asyncio.sleep(0.02)
        assert result.value.value == last

    @pytest.mark.asyncio
    async def test_standalone_bridge_requires_explicit_aclose(self):
        result = to_signal(_counting(), 0)
        await asyncio.sleep(0.01)
        assert result.value.value > 0
        result.aclose()
        last = result.value.value
        await asyncio.sleep(0.02)
        assert result.value.value == last
        assert result.error.value is None

    @pytest.mark.asyncio
    async def test_component_destroy_removes_to_async_iter_subscription(self):
        ctx = _make_context()
        sig = Signal(0)
        token = _active_component_context.set(ctx)
        try:
            iterator = to_async_iter(sig)
        finally:
            _active_component_context.reset(token)

        hooks = ctx.__get_lifecyclehooks__()
        assert "on_before_destroy" in hooks
        hooks["on_before_destroy"]()
        assert sig.consumers is None

        collected: list[int] = []

        async def collect():
            async for v in iterator:
                collected.append(v)

        task = asyncio.ensure_future(collect())
        await asyncio.sleep(0.05)
        assert collected == []
        sig.value = 1
        await asyncio.sleep(0.01)
        assert collected == []
        await task

    @pytest.mark.asyncio
    async def test_standalone_to_async_iter_survives_without_context(self):
        sig = Signal(0)
        collected: list[int] = []

        async def collect():
            async for v in to_async_iter(sig):
                collected.append(v)
                if len(collected) >= 1:
                    break

        task = asyncio.ensure_future(collect())
        await asyncio.sleep(0)
        sig.value = 3
        await task
        assert collected == [3]


async def _three_items():
    for item in ["a", "b", "b"]:
        yield item
        await asyncio.sleep(0)


async def _three_numbers():
    for item in [1, 2, 3]:
        yield item
        await asyncio.sleep(0)
