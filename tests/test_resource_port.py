from __future__ import annotations

import pytest

from webcompy.ports import RESOURCE_PORT_KEY, ResourcePort
from webcompy.ports._keys import FETCH_PORT_KEY
from webcompy.ports._resource import ResourceNotFoundError


class TestResourcePortABC:
    def test_cannot_instantiate_directly(self):
        with pytest.raises(TypeError):
            ResourcePort()  # type: ignore[abstract]

    def test_subclass_missing_one_method_cannot_instantiate(self):
        class Incomplete(ResourcePort):
            async def load_bytes(self, path: str) -> bytes:
                return b""

        with pytest.raises(TypeError):
            Incomplete()  # type: ignore[abstract]

    def test_subclass_implementing_both_methods_can_instantiate(self):
        class Complete(ResourcePort):
            async def load_text(self, path: str) -> str:
                return ""

            async def load_bytes(self, path: str) -> bytes:
                return b""

        port = Complete()
        assert port is not None


class TestResourceNotFoundError:
    def test_message_includes_path(self):
        exc = ResourceNotFoundError("templates/missing.html", "server")
        assert "templates/missing.html" in str(exc)

    def test_message_includes_context(self):
        exc = ResourceNotFoundError("a.html", "browser")
        assert "browser" in str(exc)

    def test_message_with_reason(self):
        exc = ResourceNotFoundError("a.html", "server", reason="not in allow-list")
        assert "not in allow-list" in str(exc)

    def test_path_attribute(self):
        exc = ResourceNotFoundError("a/b.html", "server")
        assert exc.path == "a/b.html"

    def test_context_attribute(self):
        exc = ResourceNotFoundError("a.html", "browser")
        assert exc.context == "browser"

    def test_default_reason_omitted(self):
        exc = ResourceNotFoundError("a.html", "server")
        assert str(exc) == "Resource not found: a.html (server)"


class TestResourcePortKey:
    def test_key_importable_from_webcompy_ports(self):
        assert RESOURCE_PORT_KEY is not None

    def test_key_distinct_from_other_port_keys(self):
        assert RESOURCE_PORT_KEY is not FETCH_PORT_KEY

    def test_key_name(self):
        assert RESOURCE_PORT_KEY.name == "webcompy-port-resource"
