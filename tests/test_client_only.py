from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from webcompy.elements.types._client_only import ClientOnlyElement
from webcompy.elements.types._element import Element
from webcompy.elements.types._text import TextElement


def _make_fake_parent() -> Element:
    from tests.conftest import FakeDOMNode

    parent = Element("div")
    parent._node_cache = FakeDOMNode("div")
    parent._mounted = True
    return parent


class TestClientOnlySSR:
    @pytest.mark.asyncio
    async def test_ssr_with_fallback(self, server_di_scope):
        children_gen = MagicMock(return_value=TextElement("browser-content"))
        fallback_gen = MagicMock(return_value=TextElement("loading"))
        el = ClientOnlyElement(children=children_gen, fallback=fallback_gen)
        parent = _make_fake_parent()
        el._parent = parent
        el._node_idx = 0
        await el._render()
        children_gen.assert_not_called()
        fallback_gen.assert_called_once()

    @pytest.mark.asyncio
    async def test_ssr_without_fallback(self, server_di_scope):
        children_gen = MagicMock(return_value=TextElement("browser-content"))
        el = ClientOnlyElement(children=children_gen)
        parent = _make_fake_parent()
        el._parent = parent
        el._node_idx = 0
        await el._render()
        children_gen.assert_not_called()
        assert len(el._children) == 1
        assert isinstance(el._children[0], TextElement)
        assert el._children[0]._get_text() == ""

    @pytest.mark.asyncio
    async def test_ssr_children_side_effects_not_triggered(self, server_di_scope):
        signal_created = False

        def side_effect_children():
            nonlocal signal_created
            signal_created = True
            return TextElement("chart")

        el = ClientOnlyElement(children=side_effect_children, fallback=lambda: TextElement("loading"))
        parent = _make_fake_parent()
        el._parent = parent
        el._node_idx = 0
        await el._render()
        assert not signal_created

    @pytest.mark.asyncio
    async def test_client_only_generator_function(self, server_di_scope):
        from webcompy.elements.generators import client_only

        result = client_only(children=lambda: TextElement("content"), fallback=lambda: TextElement("fallback"))
        assert isinstance(result, ClientOnlyElement)

    def test_exported_alias(self):
        from webcompy.elements import ClientOnly

        assert ClientOnly is ClientOnlyElement

    def test_client_only_imported(self):
        from webcompy.elements import client_only
        from webcompy.elements.generators import client_only as gen_client_only

        assert client_only is gen_client_only


class TestClientOnlyBrowser:
    @pytest.mark.asyncio
    async def test_browser_renders_children(self, fake_browser_full, monkeypatch):
        monkeypatch.setattr("webcompy.elements.types._client_only.ENVIRONMENT", "pyscript")

        children_gen = MagicMock(return_value=TextElement("interactive"))
        fallback_gen = MagicMock(return_value=TextElement("loading"))
        el = ClientOnlyElement(children=children_gen, fallback=fallback_gen)
        assert el._is_client
        parent = _make_fake_parent()
        el._parent = parent
        el._node_idx = 0
        await el._render()
        children_gen.assert_called_once()
        fallback_gen.assert_not_called()

    @pytest.mark.asyncio
    async def test_browser_without_fallback(self, fake_browser_full, monkeypatch):
        monkeypatch.setattr("webcompy.elements.types._client_only.ENVIRONMENT", "pyscript")

        children_gen = MagicMock(return_value=TextElement("content"))
        el = ClientOnlyElement(children=children_gen)
        assert el._is_client
        parent = _make_fake_parent()
        el._parent = parent
        el._node_idx = 0
        await el._render()
        children_gen.assert_called_once()
        assert len(el._children) == 1
        assert isinstance(el._children[0], TextElement)
        assert el._children[0]._get_text() == "content"


class TestClientOnlyHydration:
    @pytest.mark.asyncio
    async def test_hydration_replaces_fallback_with_children(self, fake_browser_full, monkeypatch):
        monkeypatch.setattr("webcompy.elements.types._client_only.ENVIRONMENT", "pyscript")

        parent_node = _make_fake_parent()
        ssr_el = ClientOnlyElement(
            children=lambda: TextElement("interactive"),
            fallback=lambda: TextElement("loading"),
        )
        ssr_el._parent = parent_node
        ssr_el._node_idx = 0
        await ssr_el._render()
        assert len(ssr_el._children) == 1
        assert parent_node._node_cache.childNodes.length >= 1

        el = ClientOnlyElement(
            children=lambda: TextElement("interactive"),
            fallback=lambda: TextElement("loading"),
        )
        assert el._is_client
        el._parent = parent_node
        el._node_idx = 0
        el._hydrate_node()
        assert len(el._children) == 1
        assert isinstance(el._children[0], TextElement)
        assert el._children[0]._get_text() == "interactive"

    @pytest.mark.asyncio
    async def test_hydration_replaces_empty_placeholder_with_children(self, fake_browser_full, monkeypatch):
        monkeypatch.setattr("webcompy.elements.types._client_only.ENVIRONMENT", "pyscript")

        parent_node = _make_fake_parent()
        ssr_el = ClientOnlyElement(children=lambda: TextElement("content"))
        ssr_el._parent = parent_node
        ssr_el._node_idx = 0
        await ssr_el._render()
        assert len(ssr_el._children) == 1

        el = ClientOnlyElement(children=lambda: TextElement("content"))
        assert el._is_client
        el._parent = parent_node
        el._node_idx = 0
        el._hydrate_node()
        assert len(el._children) == 1
        assert isinstance(el._children[0], TextElement)
        assert el._children[0]._get_text() == "content"
