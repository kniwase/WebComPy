from __future__ import annotations

import pytest

from webcompy.ports import ResourceNotFoundError
from webcompy_server.ports._resource import ServerResourcePort


@pytest.fixture
def app_package(tmp_path):
    """Create a temporary app package directory with a few resource files."""
    pkg = tmp_path / "app"
    pkg.mkdir()
    (pkg / "a.html").write_text("<p>hello</p>", encoding="utf-8")
    (pkg / "b.png").write_bytes(b"\x89PNG_FAKE")
    (pkg / "nested").mkdir()
    (pkg / "nested" / "c.css").write_text("body { color: red; }", encoding="utf-8")
    return pkg


class TestServerResourcePortLoadText:
    @pytest.mark.asyncio
    async def test_happy_path_returns_utf8_decoded_text(self, app_package):
        allow_list = frozenset({"a.html"})
        port = ServerResourcePort(app_package, allow_list)
        text = await port.load_text("a.html")
        assert text == "<p>hello</p>"

    @pytest.mark.asyncio
    async def test_nested_path(self, app_package):
        allow_list = frozenset({"nested/c.css"})
        port = ServerResourcePort(app_package, allow_list)
        text = await port.load_text("nested/c.css")
        assert text == "body { color: red; }"


class TestServerResourcePortLoadBytes:
    @pytest.mark.asyncio
    async def test_happy_path_returns_raw_bytes(self, app_package):
        allow_list = frozenset({"b.png"})
        port = ServerResourcePort(app_package, allow_list)
        content = await port.load_bytes("b.png")
        assert content == b"\x89PNG_FAKE"


class TestServerResourcePortFailures:
    @pytest.mark.asyncio
    async def test_missing_file_raises(self, app_package):
        allow_list = frozenset({"missing.html"})
        port = ServerResourcePort(app_package, allow_list)
        with pytest.raises(ResourceNotFoundError, match=r"missing\.html"):
            await port.load_text("missing.html")

    @pytest.mark.asyncio
    async def test_path_traversal_rejected_without_fs_access(self, app_package):
        (app_package.parent / "escape.txt").write_text("secret", encoding="utf-8")
        allow_list = frozenset({"a.html"})
        port = ServerResourcePort(app_package, allow_list)
        with pytest.raises(ResourceNotFoundError):
            await port.load_text("../escape.txt")

    @pytest.mark.asyncio
    async def test_outside_allow_list_raises_without_fs_access(self, app_package):
        allow_list = frozenset({"a.html"})
        port = ServerResourcePort(app_package, allow_list)
        with pytest.raises(ResourceNotFoundError, match=r"b\.png"):
            await port.load_bytes("b.png")

    @pytest.mark.asyncio
    async def test_empty_path_rejected(self, app_package):
        allow_list = frozenset({""})
        port = ServerResourcePort(app_package, allow_list)
        with pytest.raises(ResourceNotFoundError):
            await port.load_text("")

    @pytest.mark.asyncio
    async def test_leading_slash_rejected(self, app_package):
        allow_list = frozenset({"/etc/passwd"})
        port = ServerResourcePort(app_package, allow_list)
        with pytest.raises(ResourceNotFoundError):
            await port.load_text("/etc/passwd")

    @pytest.mark.asyncio
    async def test_symlink_escape_rejected(self, app_package):
        (app_package / "escape_link").symlink_to("/etc/passwd")
        allow_list = frozenset({"escape_link"})
        port = ServerResourcePort(app_package, allow_list)
        with pytest.raises(ResourceNotFoundError):
            await port.load_text("escape_link")


class TestServerResourcePortRecorded:
    @pytest.mark.asyncio
    async def test_successful_loads_recorded(self, app_package):
        allow_list = frozenset({"a.html", "b.png"})
        port = ServerResourcePort(app_package, allow_list)
        await port.load_text("a.html")
        await port.load_bytes("b.png")
        recorded = port.get_recorded_resources()
        assert recorded["a.html"] == b"<p>hello</p>"
        assert recorded["b.png"] == b"\x89PNG_FAKE"

    @pytest.mark.asyncio
    async def test_failed_loads_not_recorded(self, app_package):
        allow_list = frozenset({"a.html"})
        port = ServerResourcePort(app_package, allow_list)
        with pytest.raises(ResourceNotFoundError):
            await port.load_bytes("b.png")
        assert port.get_recorded_resources() == {}

    @pytest.mark.asyncio
    async def test_no_caching_between_calls(self, app_package):
        allow_list = frozenset({"a.html"})
        port = ServerResourcePort(app_package, allow_list)
        first = await port.load_text("a.html")
        (app_package / "a.html").write_text("<p>updated</p>", encoding="utf-8")
        second = await port.load_text("a.html")
        assert first == "<p>hello</p>"
        assert second == "<p>updated</p>"
        assert second != first
