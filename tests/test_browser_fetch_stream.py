from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any

import pytest

from webcompy.ports._browser._fetch import _BrowserFetchStream


class _Chunk:
    def __init__(self, done: bool, value: bytes = b"") -> None:
        self.done = done
        self.value = value


class _ScriptedReader:
    def __init__(self, results: list[Any]) -> None:
        self._results = list(results)
        self.cancelled = False
        self.read_count = 0

    async def read(self) -> Any:
        self.read_count += 1
        if self._results:
            return self._results.pop(0)
        return _Chunk(done=True)

    def cancel(self) -> None:
        self.cancelled = True


class _BlockingReader:
    def __init__(self) -> None:
        self.started = asyncio.Event()
        self.release = asyncio.Event()
        self.cancelled = False

    async def read(self) -> Any:
        self.started.set()
        await self.release.wait()
        if self.cancelled:
            raise RuntimeError("stream aborted")
        return _Chunk(done=True)

    def cancel(self) -> None:
        self.cancelled = True
        self.release.set()


class _ErroringReader:
    def __init__(self) -> None:
        self.cancelled = False

    async def read(self) -> Any:
        raise RuntimeError("network error")

    def cancel(self) -> None:
        self.cancelled = True


class _ScriptedDecoder:
    def __init__(self, texts: list[str] | None = None) -> None:
        self._texts = list(texts or [])
        self.calls = 0

    def decode(self, data: bytes = b"", stream: bool = False) -> str:
        self.calls += 1
        if self._texts:
            return self._texts.pop(0)
        return ""


class _FakeController:
    def __init__(self) -> None:
        self.aborted = False

    def abort(self) -> None:
        self.aborted = True


def _make_stream(reader: Any, decoder: Any | None = None) -> _BrowserFetchStream:
    return _BrowserFetchStream(
        200, {"content-type": "text/event-stream"}, True, reader, decoder or _ScriptedDecoder(), _FakeController()
    )


class TestIncrementalDecoding:
    @pytest.mark.asyncio
    async def test_chunks_are_decoded_incrementally(self) -> None:
        reader = _ScriptedReader([_Chunk(False, b"a"), _Chunk(False, b"b"), _Chunk(True)])
        stream = _make_stream(reader, _ScriptedDecoder(["A", "B", ""]))
        assert await stream.__anext__() == "A"
        assert await stream.__anext__() == "B"
        with pytest.raises(StopAsyncIteration):
            await stream.__anext__()

    @pytest.mark.asyncio
    async def test_empty_decoded_chunks_are_skipped(self) -> None:
        reader = _ScriptedReader([_Chunk(False, b"x"), _Chunk(False, b"y"), _Chunk(True)])
        stream = _make_stream(reader, _ScriptedDecoder(["", "", "tail"]))
        assert await stream.__anext__() == "tail"
        assert reader.read_count >= 3
        with pytest.raises(StopAsyncIteration):
            await stream.__anext__()

    @pytest.mark.asyncio
    async def test_done_tail_is_returned_once_then_finishes(self) -> None:
        reader = _ScriptedReader([_Chunk(True)])
        stream = _make_stream(reader, _ScriptedDecoder(["tail"]))
        assert await stream.__anext__() == "tail"
        with pytest.raises(StopAsyncIteration):
            await stream.__anext__()


class TestCloseSemantics:
    @pytest.mark.asyncio
    async def test_close_before_iteration_finishes_without_yielding(self) -> None:
        reader = _ScriptedReader([_Chunk(False, b"a")])
        stream = _make_stream(reader)
        stream.close()
        assert reader.cancelled
        with pytest.raises(StopAsyncIteration):
            await stream.__anext__()

    @pytest.mark.asyncio
    async def test_close_mid_read_finishes_iteration_without_error(self) -> None:
        reader = _BlockingReader()
        stream = _make_stream(reader)
        task = asyncio.ensure_future(stream.__anext__())
        await reader.started.wait()
        stream.close()
        with pytest.raises(StopAsyncIteration):
            await task
        assert reader.cancelled
        assert stream._closed

    @pytest.mark.asyncio
    async def test_close_is_idempotent_and_aborts_once(self) -> None:
        reader = _ScriptedReader([_Chunk(False, b"a")])
        decoder = _ScriptedDecoder(["a"])
        controller = _FakeController()
        stream = _BrowserFetchStream(200, {}, True, reader, decoder, controller)
        assert await stream.__anext__() == "a"
        stream.close()
        stream.close()
        await stream.aclose()
        assert reader.cancelled
        assert controller.aborted
        with pytest.raises(StopAsyncIteration):
            await stream.__anext__()

    @pytest.mark.asyncio
    async def test_read_error_without_close_propagates(self) -> None:
        reader = _ErroringReader()
        stream = _make_stream(reader)
        with pytest.raises(RuntimeError, match="network error"):
            await stream.__anext__()


class TestBrowserStreamAbortOnCancel:
    class _FakeAbortController:
        def __init__(self) -> None:
            self.signal = object()
            self.aborted = False

        def abort(self) -> None:
            self.aborted = True

    class _FakeHeaders:
        def set(self, key: str, value: str) -> None: ...

    class _FakeHeadersFactory:
        def new(self) -> TestBrowserStreamAbortOnCancel._FakeHeaders:
            return TestBrowserStreamAbortOnCancel._FakeHeaders()

    class _FakeBrowser:
        def __init__(self) -> None:
            self.controller: TestBrowserStreamAbortOnCancel._FakeAbortController | None = None
            self.Headers = TestBrowserStreamAbortOnCancel._FakeHeadersFactory()
            self.AbortController = SimpleNamespace(new=self._make_controller)
            self.fetch_called = False
            self._release = asyncio.Event()

        def _make_controller(self) -> TestBrowserStreamAbortOnCancel._FakeAbortController:
            controller = TestBrowserStreamAbortOnCancel._FakeAbortController()
            self.controller = controller
            return controller

        async def fetch(self, *args: Any, **kwargs: Any) -> Any:
            self.fetch_called = True
            await self._release.wait()
            return SimpleNamespace(
                headers=SimpleNamespace(keys=lambda: [], values=lambda: []),
                body=None,
                status=200,
                statusText="OK",
                ok=True,
            )

    def _make_port(self) -> tuple[Any, TestBrowserStreamAbortOnCancel._FakeBrowser]:
        from webcompy.ports._browser._fetch import BrowserFetchPort

        browser = self._FakeBrowser()
        port = object.__new__(BrowserFetchPort)
        port._browser = browser
        return port, browser

    @pytest.mark.asyncio
    async def test_cancel_during_open_aborts_the_fetch(self) -> None:
        port, browser = self._make_port()
        task = asyncio.ensure_future(port.stream("/data", method="POST", body="x", headers={"X-A": "1"}))
        await asyncio.sleep(0)
        assert browser.fetch_called
        assert browser.controller is not None
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert browser.controller.aborted

    @pytest.mark.asyncio
    async def test_fetch_failure_aborts_and_propagates(self) -> None:
        port, browser = self._make_port()

        async def _failing_fetch(*args: Any, **kwargs: Any) -> Any:
            raise RuntimeError("network error")

        browser.fetch = _failing_fetch  # type: ignore[method-assign]
        with pytest.raises(RuntimeError, match="network error"):
            await port.stream("/data", method="POST", body="x")
        assert browser.controller is not None
        assert browser.controller.aborted

    @pytest.mark.asyncio
    async def test_successful_open_does_not_abort(self) -> None:
        port, browser = self._make_port()
        browser._release.set()
        stream = await port.stream("/data", method="POST", body="x")
        assert browser.controller is not None
        assert browser.controller.aborted is False
        assert stream is not None
