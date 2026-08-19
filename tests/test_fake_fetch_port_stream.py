from __future__ import annotations

import pytest

from webcompy.ports import FetchStream
from webcompy.ports._fetch import Response
from webcompy_testing import FakeFetchPort


async def _collect(stream: FetchStream) -> list[str]:
    out: list[str] = []
    async for chunk in stream:
        out.append(chunk)
    return out


def _response(text: str, *, status: int = 200, ok: bool = True) -> Response:
    return Response(
        text=text, headers={"content-type": "text/event-stream"}, status_code=status, status_text="OK", ok=ok
    )


class TestScriptedStreams:
    @pytest.mark.asyncio
    async def test_scripted_chunks_are_yielded_in_order(self) -> None:
        port = FakeFetchPort(streams={("GET", "/s"): ["a", "b"]})
        stream = await port.stream("/s")
        assert await _collect(stream) == ["a", "b"]

    @pytest.mark.asyncio
    async def test_scripted_stream_default_metadata(self) -> None:
        port = FakeFetchPort(streams={("GET", "/s"): ["a"]})
        stream = await port.stream("/s")
        assert stream.status_code == 200
        assert stream.ok is True
        assert stream.headers == {"content-type": "text/event-stream"}

    @pytest.mark.asyncio
    async def test_canned_response_degrades_to_a_single_chunk(self) -> None:
        port = FakeFetchPort(responses={("GET", "/s"): _response("xyz")})
        stream = await port.stream("/s")
        assert await _collect(stream) == ["xyz"]

    @pytest.mark.asyncio
    async def test_metadata_comes_from_the_canned_response(self) -> None:
        port = FakeFetchPort(
            responses={("POST", "/s"): _response("body", status=201, ok=True)},
            streams={("POST", "/s"): ["a", "b"]},
        )
        stream = await port.stream("/s", method="POST")
        assert stream.status_code == 201
        assert stream.ok is True
        assert stream.headers == {"content-type": "text/event-stream"}
        assert await _collect(stream) == ["a", "b"]

    @pytest.mark.asyncio
    async def test_unregistered_stream_raises_key_error(self) -> None:
        port = FakeFetchPort(streams={("GET", "/known"): ["a"]})
        with pytest.raises(KeyError, match="No scripted stream or canned response"):
            await port.stream("/unknown")

    @pytest.mark.asyncio
    async def test_unregistered_stream_lists_available_keys(self) -> None:
        port = FakeFetchPort(streams={("GET", "/known"): ["a"]})
        with pytest.raises(KeyError) as excinfo:
            await port.stream("/unknown")
        assert "/known" in str(excinfo.value)
        assert "GET" in str(excinfo.value)


class TestCloseSemantics:
    @pytest.mark.asyncio
    async def test_close_records_the_abort(self) -> None:
        port = FakeFetchPort(streams={("GET", "/s"): ["a", "b"]})
        stream = await port.stream("/s")
        assert port.aborted_streams == []
        stream.close()
        assert port.aborted_streams == [("GET", "/s")]
        assert stream.aborted is True

    @pytest.mark.asyncio
    async def test_close_is_idempotent(self) -> None:
        port = FakeFetchPort(streams={("GET", "/s"): ["a", "b"]})
        stream = await port.stream("/s")
        stream.close()
        stream.close()
        await stream.aclose()
        assert port.aborted_streams == [("GET", "/s")]

    @pytest.mark.asyncio
    async def test_subsequent_iteration_finishes_after_close(self) -> None:
        port = FakeFetchPort(streams={("GET", "/s"): ["a", "b"]})
        stream = await port.stream("/s")
        assert await stream.__anext__() == "a"
        stream.close()
        assert await _collect(stream) == []
