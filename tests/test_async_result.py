import asyncio

from webcompy.aio._async_result import AsyncResult, AsyncState


class TestAsyncResultState:
    def test_initial_state(self):
        async def fetch():
            return 42

        result = AsyncResult(fetch)
        assert result.state.value == AsyncState.PENDING
        assert result.is_pending.value is True
        assert result.is_loading.value is False
        assert result.is_success.value is False
        assert result.is_error.value is False

    def test_refetch_transitions_to_success(self):
        async def fetch():
            return 42

        result = AsyncResult(fetch)
        result.refetch()

        assert result.state.value == AsyncState.SUCCESS
        assert result.is_success.value is True
        assert result.data.value == 42
        assert result.error.value is None

    def test_refetch_transitions_to_error(self):
        async def fetch():
            raise ValueError("boom")

        result = AsyncResult(fetch)
        result.refetch()

        assert result.state.value == AsyncState.ERROR
        assert result.is_error.value is True
        assert isinstance(result.error.value, ValueError)
        assert result.data.value is None


class TestAsyncResultSWR:
    def test_refetch_preserves_stale_data(self):
        counter = 0

        async def fetch():
            nonlocal counter
            counter += 1
            return counter

        result = AsyncResult(fetch)
        result.refetch()
        assert result.data.value == 1

        result.refetch()
        assert result.data.value == 2

    def test_error_preserves_last_data(self):
        should_fail = False

        async def fetch():
            if should_fail:
                raise RuntimeError("fail")
            return "good"

        result = AsyncResult(fetch)
        result.refetch()
        assert result.data.value == "good"

        should_fail = True
        result.refetch()
        assert result.state.value == AsyncState.ERROR
        assert result.data.value == "good"

    def test_error_with_no_prior_success_has_no_data(self):
        async def fetch():
            raise RuntimeError("always fail")

        result = AsyncResult(fetch)
        result.refetch()
        assert result.state.value == AsyncState.ERROR
        assert result.data.value is None


class TestAsyncResultDefault:
    def test_default_value_is_used_initially(self):
        result = AsyncResult(lambda: asyncio.sleep(0), default=[])
        assert result.data.value == []

    def test_default_replaced_on_success(self):
        async def fetch():
            return [1, 2, 3]

        result = AsyncResult(fetch, default=[])
        result.refetch()
        assert result.data.value == [1, 2, 3]

    def test_default_preserved_on_error_with_no_prior_success(self):
        async def fetch():
            raise ValueError("oops")

        result = AsyncResult(fetch, default=[])
        result.refetch()
        assert result.data.value == []

    def test_error_preserves_last_data_over_default(self):
        should_fail = False

        async def fetch():
            if should_fail:
                raise RuntimeError("fail")
            return [1, 2]

        result = AsyncResult(fetch, default=[])
        result.refetch()
        assert result.data.value == [1, 2]

        should_fail = True
        result.refetch()
        assert result.data.value == [1, 2]


class TestAsyncResultWatch:
    def test_watch_trigger_refetch_on_change(self):
        query = "a"
        call_count = 0

        async def fetch():
            nonlocal call_count
            call_count += 1
            return query

        result = AsyncResult(fetch, default="")
        result.refetch()
        assert call_count == 1


class TestAsyncResultComputedPredicates:
    def test_predicates_are_mutually_exclusive_after_success(self):
        async def fetch():
            return "ok"

        result = AsyncResult(fetch)
        result.refetch()

        assert result.is_success.value is True
        assert result.is_loading.value is False
        assert result.is_error.value is False

    def test_predicates_are_mutually_exclusive_after_error(self):
        async def fetch():
            raise RuntimeError("err")

        result = AsyncResult(fetch)
        result.refetch()

        assert result.is_error.value is True
        assert result.is_loading.value is False
        assert result.is_success.value is False
