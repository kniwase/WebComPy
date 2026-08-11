from __future__ import annotations

import logging as std_logging

import pytest

from webcompy.components import define_component
from webcompy.elements import Teleport, html, repeat, switch
from webcompy.elements.types._element import Element
from webcompy.elements.types._text import TextElement
from webcompy.signal import ReactiveList, Signal
from webcompy_testing import TestRenderer


@pytest.fixture
def teleport_env(monkeypatch):
    monkeypatch.setattr("webcompy.elements.types._teleport.ENVIRONMENT", "pyscript")


def _body_children_by_tag(body, tag: str) -> list:
    return [body.childNodes[i] for i in range(body.childNodes.length) if body.childNodes[i].nodeName == tag]


def _find_by_attr(body, tag: str, attr: str, value: str):
    for i in range(body.childNodes.length):
        child = body.childNodes[i]
        if child.nodeName == tag and child.getAttribute(attr) == value:
            return child
    return None


class TestTeleportMount:
    def test_children_mount_under_body_and_anchor_at_logical_position(self, teleport_env):
        @define_component
        def Page(context):
            return html.DIV(
                {},
                Teleport({"to": "body"}, html.DIV({"id": "modal"}, "modal-content")),
            )

        with TestRenderer.render(Page) as result:
            body = result.body_node
            assert body is not None
            modal = _find_by_attr(body, "DIV", "id", "modal")
            assert modal is not None
            assert modal.parentNode is body
            root_children = result._root_node.childNodes
            assert root_children.length == 1
            assert root_children[0].nodeName == "#text"
            assert (root_children[0].textContent or "") == ""


class TestTeleportSiblingStability:
    def test_sibling_positions_stable_while_teleported_content_changes(self, teleport_env):
        items = ReactiveList(["x", "y"])

        @define_component
        def Page(context):
            return html.DIV(
                {},
                html.P({}, "before"),
                Teleport({"to": "body"}, repeat(items, lambda item: html.DIV({"data-t": "teleported"}, item))),
                html.P({}, "after"),
            )

        def _logical_texts(result):
            return [(c.textContent or "") for c in result._root_node.childNodes]

        def _teleported_texts(body):
            return [
                (body.childNodes[i].textContent or "")
                for i in range(body.childNodes.length)
                if body.childNodes[i].getAttribute("data-t") == "teleported"
            ]

        with TestRenderer.render(Page) as result:
            body = result.body_node
            assert body is not None
            assert _teleported_texts(body) == ["x", "y"]
            assert _logical_texts(result) == ["before", "", "after"]
            items.pop(0)
            assert _teleported_texts(body) == ["y"]
            assert _logical_texts(result) == ["before", "", "after"]
            items.append("z")
            assert _teleported_texts(body) == ["y", "z"]
            assert _logical_texts(result) == ["before", "", "after"]


class TestTeleportMissingTarget:
    def test_missing_target_falls_back_inline_with_warning(self, teleport_env, caplog):
        @define_component
        def Page(context):
            return html.DIV(
                {},
                html.P({}, "before"),
                Teleport({"to": "#nonexistent-root"}, html.SPAN({}, "inline-content")),
                html.P({}, "after"),
            )

        with caplog.at_level(std_logging.WARNING, logger="uvicorn"), TestRenderer.render(Page) as result:
            names = [(c.nodeName, c.textContent or "") for c in result._root_node.childNodes]
            assert names == [("P", "before"), ("SPAN", "inline-content"), ("P", "after")]
        assert any("Teleport target" in r.message for r in caplog.records)


class TestTeleportMultipleTargets:
    def test_multiple_teleports_append_in_mount_order(self, teleport_env):
        @define_component
        def Page(context):
            return html.DIV(
                {},
                Teleport({"to": "body"}, html.DIV({"data-t": "teleported"}, "content-A")),
                Teleport({"to": "body"}, html.DIV({"data-t": "teleported"}, "content-B")),
            )

        with TestRenderer.render(Page) as result:
            body = result.body_node
            assert body is not None
            texts = [
                (body.childNodes[i].textContent or "")
                for i in range(body.childNodes.length)
                if body.childNodes[i].getAttribute("data-t") == "teleported"
            ]
            assert texts == ["content-A", "content-B"]


class TestTeleportRemoval:
    def test_conditional_removal_cleans_target_and_anchor(self, teleport_env):
        open_state = Signal(True)

        @define_component
        def Page(context):
            return html.DIV(
                {},
                html.P({}, "before"),
                switch(
                    {
                        "case": open_state,
                        "generator": lambda: Teleport({"to": "body"}, html.DIV({"id": "modal"}, "modal-content")),
                    },
                    default=None,
                ),
                html.P({}, "after"),
            )

        def _has_modal(body):
            return _find_by_attr(body, "DIV", "id", "modal") is not None

        with TestRenderer.render(Page) as result:
            body = result.body_node
            assert body is not None
            assert _has_modal(body)
            assert result._root_node.childNodes.length == 3
            open_state.value = False
            assert not _has_modal(body)
            assert result._root_node.childNodes.length == 2
            open_state.value = True
            assert _has_modal(body)
            assert result._root_node.childNodes.length == 3


class TestTeleportReactivity:
    def test_reactive_update_applies_at_target(self, teleport_env):
        message = Signal("initial")

        @define_component
        def Page(context):
            return html.DIV({}, Teleport({"to": "body"}, html.SPAN({}, message)))

        with TestRenderer.render(Page) as result:
            body = result.body_node
            assert body is not None
            spans = _body_children_by_tag(body, "SPAN")
            assert len(spans) == 1
            assert spans[0].textContent == "initial"
            message.value = "updated"
            assert spans[0].textContent == "updated"
            assert result._root_node.childNodes.length == 1

    def test_scoped_attrs_and_event_handlers_survive_relocation(self, teleport_env):
        clicked: list[int] = []

        @define_component
        def Modal(context):
            return html.BUTTON({"class": "modal-btn", "@click": lambda ev: clicked.append(1)}, "click me")

        Modal.scoped_style = {" .modal-btn": {"color": "red"}}

        @define_component
        def Page(context):
            return html.DIV({}, Teleport({"to": "body"}, Modal(None)))

        with TestRenderer.render(Page) as result:
            body = result.body_node
            assert body is not None
            buttons = _body_children_by_tag(body, "BUTTON")
            assert len(buttons) == 1
            btn = buttons[0]
            assert btn.getAttribute("class") == "modal-btn"
            assert any(name.startswith("webcompy-cid-") for name in btn.getAttributeNames())
            assert any(et == "click" for et, _ in btn._event_listeners)
            from webcompy_server.ports import VirtualDOMEvent

            btn.dispatchEvent(VirtualDOMEvent("click"))
            assert clicked == [1]


class TestTeleportHydration:
    @pytest.mark.asyncio
    async def test_hydration_adopts_anchor_and_mounts_children_client_side(self, teleport_env, fake_browser_full):
        from tests.conftest import FakeDOMNode
        from tests.test_dynamic_child_node_index import _FakeRootElement
        from webcompy.di import inject
        from webcompy.ports._keys import ASYNC_SCHEDULER_PORT_KEY

        dom_port, _, _ = fake_browser_full
        parent = _FakeRootElement("div", {}, {}, None, None)
        parent._node_cache = FakeDOMNode("div")
        parent._mounted = True
        prerendered_anchor = FakeDOMNode("#text", text_content="")
        prerendered_anchor.__webcompy_prerendered_node__ = True
        parent._node_cache.appendChild(prerendered_anchor)

        teleport = Teleport({"to": "body"}, Element("span", {}, {}, None, [TextElement("teleported")]))
        teleport._parent = parent
        teleport._node_idx = 0
        teleport._hydrate_node()
        assert teleport._node_cache is prerendered_anchor
        assert teleport._mounted is True

        await inject(ASYNC_SCHEDULER_PORT_KEY).await_pending()
        body = dom_port.body
        spans = [body.childNodes[i] for i in range(body.childNodes.length) if body.childNodes[i].nodeName == "SPAN"]
        assert len(spans) == 1
        assert spans[0].textContent == "teleported"
