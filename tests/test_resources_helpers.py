from __future__ import annotations

from pathlib import Path

import pytest

from webcompy.di._keys import RESOURCE_DATA_KEY
from webcompy.di._scope import DIScope, _active_di_scope
from webcompy.exception import WebComPyException
from webcompy.ports._keys import RESOURCE_PORT_KEY
from webcompy.resources import load_bytes, load_text


class _FakeResourcePort:
    def __init__(self, response_pairs: dict[str, str | bytes]) -> None:
        self._text_calls: list[str] = []
        self._bytes_calls: list[str] = []
        self._text_responses = {k: v for k, v in response_pairs.items() if isinstance(v, str)}
        self._bytes_responses = {k: v for k, v in response_pairs.items() if isinstance(v, bytes)}

    async def load_text(self, path: str) -> str:
        self._text_calls.append(path)
        if path not in self._text_responses:
            raise KeyError(path)
        return self._text_responses[path]

    async def load_bytes(self, path: str) -> bytes:
        self._bytes_calls.append(path)
        if path not in self._bytes_responses:
            raise KeyError(path)
        return self._bytes_responses[path]


@pytest.fixture
def port_scope():
    scope = DIScope()
    token = _active_di_scope.set(scope)
    yield scope
    _active_di_scope.reset(token)


class TestLoadTextSourceNormalization:
    @pytest.mark.asyncio
    async def test_str_path_passed_through(self, port_scope) -> None:
        port = _FakeResourcePort({"templates/card.html": "<p>hi</p>"})
        port_scope.provide(RESOURCE_PORT_KEY, port)
        result = await load_text("templates/card.html")
        assert result == "<p>hi</p>"
        assert port._text_calls == ["templates/card.html"]

    @pytest.mark.asyncio
    async def test_relative_pathlib_path_converted_to_posix(self, port_scope) -> None:
        port = _FakeResourcePort({"templates/card.html": "ok"})
        port_scope.provide(RESOURCE_PORT_KEY, port)
        result = await load_text(Path("templates") / "card.html")
        assert result == "ok"
        assert port._text_calls == ["templates/card.html"]

    @pytest.mark.asyncio
    async def test_nested_pathlib_path(self, port_scope) -> None:
        port = _FakeResourcePort({"a/b/c.html": "deep"})
        port_scope.provide(RESOURCE_PORT_KEY, port)
        result = await load_text(Path("a") / "b" / "c.html")
        assert result == "deep"
        assert port._text_calls == ["a/b/c.html"]

    @pytest.mark.asyncio
    async def test_absolute_path_raises(self, port_scope) -> None:
        with pytest.raises(WebComPyException, match="Absolute"):
            await load_text(Path("/etc/passwd"))

    @pytest.mark.asyncio
    async def test_traversal_segment_raises_str(self, port_scope) -> None:
        with pytest.raises(WebComPyException, match=r"\.\."):
            await load_text("../secret.txt")

    @pytest.mark.asyncio
    async def test_traversal_segment_raises_path(self, port_scope) -> None:
        with pytest.raises(WebComPyException, match=r"\.\."):
            await load_text(Path("..") / "secret.txt")

    @pytest.mark.asyncio
    async def test_invalid_type_raises(self, port_scope) -> None:
        with pytest.raises(WebComPyException, match="Invalid source type"):
            await load_text(123)  # type: ignore[arg-type]


class TestLoadBytesSourceNormalization:
    @pytest.mark.asyncio
    async def test_str_path_passed_through(self, port_scope) -> None:
        port = _FakeResourcePort({"icons/star.png": b"\x89PNG_FAKE"})
        port_scope.provide(RESOURCE_PORT_KEY, port)
        result = await load_bytes("icons/star.png")
        assert result == b"\x89PNG_FAKE"

    @pytest.mark.asyncio
    async def test_relative_pathlib_path(self, port_scope) -> None:
        port = _FakeResourcePort({"a/b.png": b"x"})
        port_scope.provide(RESOURCE_PORT_KEY, port)
        result = await load_bytes(Path("a") / "b.png")
        assert result == b"x"
        assert port._bytes_calls == ["a/b.png"]

    @pytest.mark.asyncio
    async def test_absolute_path_raises(self, port_scope) -> None:
        with pytest.raises(WebComPyException, match="Absolute"):
            await load_bytes(Path("/usr/bin/sh"))

    @pytest.mark.asyncio
    async def test_traversal_raises(self, port_scope) -> None:
        with pytest.raises(WebComPyException, match=r"\.\."):
            await load_bytes("a/../../escape.txt")


class TestHelpersRequireResourcePort:
    @pytest.mark.asyncio
    async def test_load_text_missing_port_raises(self, port_scope) -> None:
        with pytest.raises(WebComPyException, match="RESOURCE_PORT_KEY"):
            await load_text("a.html")

    @pytest.mark.asyncio
    async def test_load_bytes_missing_port_raises(self, port_scope) -> None:
        with pytest.raises(WebComPyException, match="RESOURCE_PORT_KEY"):
            await load_bytes("a.html")


class TestLoadTextResourceDataIntegration:
    """The helpers use ``RESOURCE_PORT_KEY`` from the DI scope (provided by
    the render context); they don't read ``RESOURCE_DATA_KEY`` directly,
    but should compose with it via the port implementation.
    """

    @pytest.mark.asyncio
    async def test_data_in_resource_data_takes_priority(self, port_scope) -> None:
        captured: dict[str, object] = {}

        class _RecordingPort:
            async def load_text(self, path: str) -> str:
                captured["path"] = path
                return "from port"

        port_scope.provide(RESOURCE_PORT_KEY, _RecordingPort())
        port_scope.provide(RESOURCE_DATA_KEY, {"a.html": "aGVsbG8="})

        result = await load_text("a.html")
        assert result == "from port"
        assert captured["path"] == "a.html"


class TestImports:
    def test_top_level_exports(self) -> None:
        from webcompy import load_bytes as lb
        from webcompy import load_text as lt

        assert lb is load_bytes
        assert lt is load_text

    def test_load_in_modules(self) -> None:
        from webcompy import resources

        assert hasattr(resources, "load_text")
        assert hasattr(resources, "load_bytes")
