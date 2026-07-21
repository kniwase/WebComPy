from __future__ import annotations

from typing import Any

import pytest

from webcompy.ports import MARKDOWN_PORT_KEY, MarkdownPort
from webcompy.ports._keys import FETCH_PORT_KEY


class TestMarkdownPortABC:
    def test_cannot_instantiate_directly(self):
        port_class: Any = MarkdownPort
        with pytest.raises(TypeError):
            port_class()

    def test_complete_subclass_can_instantiate(self):
        class Complete(MarkdownPort):
            def render(self, source: str) -> str:
                return source

        port = Complete()
        assert port.render("text") == "text"


class TestMarkdownPortKey:
    def test_key_importable_from_webcompy_ports(self):
        assert MARKDOWN_PORT_KEY is not None

    def test_key_distinct_from_other_port_keys(self):
        assert MARKDOWN_PORT_KEY is not FETCH_PORT_KEY

    def test_key_name(self):
        assert MARKDOWN_PORT_KEY.name == "webcompy-port-markdown"
