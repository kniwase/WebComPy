from __future__ import annotations

import asyncio

from webcompy.aio._async_result import AsyncResult, AsyncState


class TestAsyncResultRestoreFromTransfer:
    def test_restoration_sets_state_to_success_with_correct_data(self):
        async def fetch():
            return "original"

        result = AsyncResult(fetch)
        result._restore_from_transfer("transferred")

        assert result.state.value == AsyncState.SUCCESS
        assert result.is_success.value is True
        assert result.data.value == "transferred"
        assert result.error.value is None

    def test_is_success_and_is_loading_computed_values_are_correct(self):
        async def fetch():
            return "data"

        result = AsyncResult(fetch)
        assert result.is_success.value is False
        assert result.is_loading.value is False
        assert result.is_pending.value is True

        result._restore_from_transfer("data")
        assert result.is_success.value is True
        assert result.is_loading.value is False
        assert result.is_pending.value is False

    def test_async_function_is_not_called_after_restoration(self):
        call_count = 0

        async def fetch():
            nonlocal call_count
            call_count += 1
            return "new"

        result = AsyncResult(fetch)
        result._restore_from_transfer("restored")

        assert call_count == 0
        assert result.data.value == "restored"

    def test_restoration_from_error_state(self):
        async def fetch():
            raise ValueError("original error")

        result = AsyncResult(fetch)
        result.refetch()

        assert result.state.value == AsyncState.ERROR
        result._restore_from_transfer("recovered")
        assert result.state.value == AsyncState.SUCCESS
        assert result.data.value == "recovered"
        assert result.error.value is None

    def test_restoration_does_not_trigger_loading_state(self):
        async def fetch():
            await asyncio.sleep(0)
            return "data"

        result = AsyncResult(fetch)
        result._restore_from_transfer("immediate")
        assert result.is_loading.value is False
        assert result.is_success.value is True

    def test_restore_with_none_data(self):
        async def fetch():
            return "val"

        result = AsyncResult(fetch, default="default")
        result._restore_from_transfer(None)
        assert result.state.value == AsyncState.SUCCESS
        assert result.data.value is None

    def test_refetch_after_restore_works_normally(self):
        call_count = 0

        async def fetch():
            nonlocal call_count
            call_count += 1
            return f"call-{call_count}"

        result = AsyncResult(fetch)
        result._restore_from_transfer("restored")
        assert result.data.value == "restored"
        assert call_count == 0

        result.refetch()
        assert call_count == 1
        assert result.data.value == "call-1"
