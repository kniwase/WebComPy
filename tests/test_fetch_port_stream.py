from __future__ import annotations

from typing import Any

import pytest

from webcompy.ports import FetchStream
from webcompy.ports._fetch import FetchPort, Response


class _ScriptedFetchPort(FetchPort):
    def __init__(self, response: Response) -> None:
        self._response = response

    async def fetch(
        self,
        url: str,
        *,
        method: str = "GET",
        headers: dict[str, str] | None = None,
        body: str | None = None,
    ) -> Response:
        return self._response


class _ChunkedFetchStream(FetchStream):
    def __init__(self, chunks: list[str]) -> None:
        super().__init__(200, {"content-type": "text/plain"}, True)
        self._chunks = iter(chunks)
        self._done = False

    async def __anext__(self) -> str:
        if self._closed or self._done:
            raise StopAsyncIteration
        try:
            chunk = next(self._chunks)
        except StopIteration:
            self._done = True
            raise StopAsyncIteration from None
        return chunk


async def _collect(stream: FetchStream) -> list[str]:
    out: list[str] = []
    async for chunk in stream:
        out.append(chunk)
    return out


class TestDefaultStream:
    @pytest.mark.asyncio
    async def test_yields_the_entire_body_as_one_chunk(self) -> None:
        port = _ScriptedFetchPort(Response(text="abc", headers={}, status_code=200, status_text="OK", ok=True))
        stream = await port.stream("/data")
        assert await _collect(stream) == ["abc"]

    @pytest.mark.asyncio
    async def test_metadata_is_available_before_body_consumption(self) -> None:
        port = _ScriptedFetchPort(
            Response(
                text="xyz", headers={"content-type": "text/plain"}, status_code=201, status_text="Created", ok=True
            )
        )
        stream = await port.stream("/data")
        assert stream.status_code == 201
        assert stream.headers == {"content-type": "text/plain"}
        assert stream.ok is True
        assert await _collect(stream) == ["xyz"]

    @pytest.mark.asyncio
    async def test_failed_status_metadata_is_available(self) -> None:
        port = _ScriptedFetchPort(Response(text="err", headers={}, status_code=500, status_text="Error", ok=False))
        stream = await port.stream("/data")
        assert stream.ok is False
        assert stream.status_code == 500

    @pytest.mark.asyncio
    async def test_close_before_iteration_finishes_without_yielding(self) -> None:
        port = _ScriptedFetchPort(Response(text="abc", headers={}, status_code=200, status_text="OK", ok=True))
        stream = await port.stream("/data")
        stream.close()
        assert await _collect(stream) == []

    @pytest.mark.asyncio
    async def test_close_mid_iteration_finishes_without_further_chunks(self) -> None:
        port = _ScriptedFetchPort(Response(text="abc", headers={}, status_code=200, status_text="OK", ok=True))
        stream = await port.stream("/data")
        first = await stream.__anext__()
        assert first == "abc"
        stream.close()
        with pytest.raises(StopAsyncIteration):
            await stream.__anext__()
        assert await _collect(stream) == []

    @pytest.mark.asyncio
    async def test_close_is_idempotent_and_aclose_delegates(self) -> None:
        port = _ScriptedFetchPort(Response(text="abc", headers={}, status_code=200, status_text="OK", ok=True))
        stream = await port.stream("/data")
        stream.close()
        stream.close()
        await stream.aclose()
        assert await _collect(stream) == []

    @pytest.mark.asyncio
    async def test_method_headers_and_body_are_forwarded(self) -> None:
        captured: list[tuple[str, str, dict[str, str] | None, str | None]] = []

        class _CapturingPort(FetchPort):
            async def fetch(
                self,
                url: str,
                *,
                method: str = "GET",
                headers: dict[str, str] | None = None,
                body: str | None = None,
            ) -> Response:
                captured.append((url, method, headers, body))
                return Response(text="ok", headers={}, status_code=200, status_text="OK", ok=True)

        port = _CapturingPort()
        await port.stream("/query", method="POST", headers={"Content-Type": "application/json"}, body='{"q":"x"}')
        assert captured == [("/query", "POST", {"Content-Type": "application/json"}, '{"q":"x"}')]


class TestChunkedStreamContract:
    @pytest.mark.asyncio
    async def test_chunks_concatenate_to_the_full_body(self) -> None:
        stream = _ChunkedFetchStream(["hel", "lo wor", "ld"])
        assert stream.status_code == 200
        assert stream.ok is True
        chunks = await _collect(stream)
        assert "".join(chunks) == "hello world"

    @pytest.mark.asyncio
    async def test_iteration_finishes_with_stop_async_iteration(self) -> None:
        stream = _ChunkedFetchStream(["a", "b"])
        assert await _collect(stream) == ["a", "b"]
        assert await _collect(stream) == []

    @pytest.mark.asyncio
    async def test_close_finishes_inflight_iteration(self) -> None:
        stream = _ChunkedFetchStream(["a", "b"])
        assert await stream.__anext__() == "a"
        stream.close()
        with pytest.raises(StopAsyncIteration):
            await stream.__anext__()
        assert await _collect(stream) == []

    @pytest.mark.asyncio
    async def test_close_is_idempotent(self) -> None:
        stream = _ChunkedFetchStream(["a"])
        stream.close()
        stream.close()
        await stream.aclose()
        assert await _collect(stream) == []

    @pytest.mark.asyncio
    async def test_stream_is_async_iterable(self) -> None:
        stream: Any = _ChunkedFetchStream(["x"])
        assert stream.__aiter__() is stream
        assert isinstance(stream, FetchStream)
