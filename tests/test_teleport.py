from __future__ import annotations

import asyncio
from html.parser import HTMLParser

import pytest

from tests.conftest import FakeDOMNode
from webcompy.components import define_component
from webcompy.elements import Teleport, html, repeat, switch
from webcompy.elements.types._element import Element
from webcompy.elements.types._teleport import TeleportElement
from webcompy.elements.types._text import TextElement
from webcompy.signal import ReactiveList, Signal
from webcompy_testing import TestRenderer, create_test_app, render_app_html


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
        @define_component()
        def TeleportPage(context):
            return html.DIV(
                {},
                Teleport({"to": "body"}, html.DIV({"id": "modal"}, "modal-content")),
            )

        with TestRenderer.render(TeleportPage) as result:
            body = result.body_node
            assert body is not None
            modal = _find_by_attr(body, "DIV", "id", "modal")
            assert modal is not None
            assert modal.parentNode is body
            root_children = result._root_node.childNodes[0].childNodes
            assert root_children.length == 1
            assert root_children[0].nodeName == "#comment"
            assert (root_children[0].textContent or "") == "webcompy-teleport-anchor"

    def test_invisible_anchor_not_matched_by_find_by_text(self, teleport_env):
        @define_component()
        def TeleportPage(context):
            return html.DIV(
                {},
                html.P({}, "before"),
                Teleport({"to": "body"}, html.DIV({"id": "modal"}, "modal-content")),
                html.P({}, "after"),
            )

        with TestRenderer.render(TeleportPage) as result:
            assert result.find_by_text("webcompy-teleport-anchor") is None
            assert result.find_by_text("before") is not None


class TestTeleportSiblingStability:
    def test_sibling_positions_stable_while_teleported_content_changes(self, teleport_env):
        items = ReactiveList(["x", "y"])

        @define_component()
        def TeleportPage(context):
            return html.DIV(
                {},
                html.P({}, "before"),
                Teleport({"to": "body"}, repeat(items, lambda item: html.DIV({"data-t": "teleported"}, item))),
                html.P({}, "after"),
            )

        def _logical_texts(result):
            return [(c.textContent or "") for c in result._root_node.childNodes[0].childNodes]

        def _teleported_texts(body):
            return [
                (body.childNodes[i].textContent or "")
                for i in range(body.childNodes.length)
                if body.childNodes[i].getAttribute("data-t") == "teleported"
            ]

        with TestRenderer.render(TeleportPage) as result:
            body = result.body_node
            assert body is not None
            assert _teleported_texts(body) == ["x", "y"]
            assert _logical_texts(result) == ["before", "webcompy-teleport-anchor", "after"]
            items.pop(0)
            assert _teleported_texts(body) == ["y"]
            assert _logical_texts(result) == ["before", "webcompy-teleport-anchor", "after"]
            items.append("z")
            assert _teleported_texts(body) == ["y", "z"]
            assert _logical_texts(result) == ["before", "webcompy-teleport-anchor", "after"]


class TestTeleportMissingTarget:
    def test_missing_target_falls_back_inline_with_warning(self, teleport_env, monkeypatch):
        warnings: list[tuple] = []
        monkeypatch.setattr("webcompy.logging.warning", lambda *values: warnings.append(values))

        @define_component()
        def TeleportPage(context):
            return html.DIV(
                {},
                html.P({}, "before"),
                Teleport({"to": "#nonexistent-root"}, html.SPAN({}, "inline-content")),
                html.P({}, "after"),
            )

        with TestRenderer.render(TeleportPage) as result:
            names = [(c.nodeName, c.textContent or "") for c in result._root_node.childNodes[0].childNodes]
            assert names == [("P", "before"), ("SPAN", "inline-content"), ("P", "after")]
        assert any("Teleport target" in str(values) for values in warnings)


class TestTeleportInlineFallbackStability:
    def test_inline_repeat_growth_keeps_trailing_siblings_stable(self, teleport_env):
        items = ReactiveList(["x", "y"])
        trailing = ReactiveList(["a"])

        @define_component()
        def TeleportPage(context):
            return html.DIV(
                {},
                html.P({"data-testid": "before"}, "before"),
                Teleport(
                    {"to": "#nonexistent-root"},
                    repeat(items, lambda item: html.SPAN({"data-t": "inline"}, item)),
                ),
                repeat(trailing, lambda item: html.SPAN({"data-t": "trailing"}, item)),
                html.P({"data-testid": "after"}, "after"),
            )

        def _node_names(result):
            return [(c.nodeName, c.textContent or "") for c in result._root_node.childNodes[0].childNodes]

        with TestRenderer.render(TeleportPage) as result:
            assert _node_names(result) == [
                ("P", "before"),
                ("SPAN", "x"),
                ("SPAN", "y"),
                ("SPAN", "a"),
                ("P", "after"),
            ]
            items.pop(0)
            assert _node_names(result) == [("P", "before"), ("SPAN", "y"), ("SPAN", "a"), ("P", "after")]
            trailing.append("b")
            assert _node_names(result) == [
                ("P", "before"),
                ("SPAN", "y"),
                ("SPAN", "a"),
                ("SPAN", "b"),
                ("P", "after"),
            ]

    def test_inline_repeat_uses_updated_index_after_preceding_sibling_grows(self, teleport_env):
        leading = ReactiveList(["a"])
        inner = ReactiveList(["x", "y"])

        @define_component()
        def TeleportPage(context):
            return html.DIV(
                {},
                repeat(leading, lambda item: html.SPAN({"data-t": "leading"}, item)),
                Teleport(
                    {"to": "#nonexistent-root"},
                    repeat(inner, lambda item: html.SPAN({"data-t": "inline"}, item)),
                ),
                html.P({"data-testid": "after"}, "after"),
            )

        def _node_names(result):
            return [(c.nodeName, c.textContent or "") for c in result._root_node.childNodes[0].childNodes]

        with TestRenderer.render(TeleportPage) as result:
            assert _node_names(result) == [
                ("SPAN", "a"),
                ("SPAN", "x"),
                ("SPAN", "y"),
                ("P", "after"),
            ]
            leading.append("b")
            assert _node_names(result) == [
                ("SPAN", "a"),
                ("SPAN", "b"),
                ("SPAN", "x"),
                ("SPAN", "y"),
                ("P", "after"),
            ]
            inner.append("z")
            assert _node_names(result) == [
                ("SPAN", "a"),
                ("SPAN", "b"),
                ("SPAN", "x"),
                ("SPAN", "y"),
                ("SPAN", "z"),
                ("P", "after"),
            ]
            inner.pop(0)
            assert _node_names(result) == [
                ("SPAN", "a"),
                ("SPAN", "b"),
                ("SPAN", "y"),
                ("SPAN", "z"),
                ("P", "after"),
            ]


class TestTeleportMultipleTargets:
    def test_multiple_teleports_append_in_mount_order(self, teleport_env):
        @define_component()
        def TeleportPage(context):
            return html.DIV(
                {},
                Teleport({"to": "body"}, html.DIV({"data-t": "teleported"}, "content-A")),
                Teleport({"to": "body"}, html.DIV({"data-t": "teleported"}, "content-B")),
            )

        with TestRenderer.render(TeleportPage) as result:
            body = result.body_node
            assert body is not None
            texts = [
                (body.childNodes[i].textContent or "")
                for i in range(body.childNodes.length)
                if body.childNodes[i].getAttribute("data-t") == "teleported"
            ]
            assert texts == ["content-A", "content-B"]


class TestTeleportSharedTargetReindex:
    def test_sibling_teleports_stay_ordered_when_shared_target_subtrees_change(self, teleport_env):
        a_items = ReactiveList(["a1"])
        b_items = ReactiveList(["b1"])

        @define_component()
        def TeleportPage(context):
            return html.DIV(
                {},
                Teleport({"to": "body"}, repeat(a_items, lambda x: html.DIV({"data-t": "a"}, x))),
                Teleport({"to": "body"}, repeat(b_items, lambda x: html.DIV({"data-t": "b"}, x))),
            )

        def _teleported_tags(body):
            return [
                (body.childNodes[i].getAttribute("data-t") or "") + (body.childNodes[i].textContent or "")
                for i in range(body.childNodes.length)
                if body.childNodes[i].getAttribute("data-t") in ("a", "b")
            ]

        with TestRenderer.render(TeleportPage) as result:
            body = result.body_node
            assert body is not None
            assert _teleported_tags(body) == ["aa1", "bb1"]
            a_items.append("a2")
            assert _teleported_tags(body) == ["aa1", "aa2", "bb1"]
            b_items.append("b2")
            assert _teleported_tags(body) == ["aa1", "aa2", "bb1", "bb2"]
            a_items.pop(0)
            assert _teleported_tags(body) == ["aa2", "bb1", "bb2"]
            b_items.pop(0)
            assert _teleported_tags(body) == ["aa2", "bb2"]

    @pytest.mark.asyncio
    async def test_shared_target_stays_ordered_while_sibling_subtree_is_pending(self, teleport_env, fake_browser_full):
        import asyncio

        from webcompy.components._component import HeadPropsStore
        from webcompy.components._generator import ComponentStore
        from webcompy.di import inject
        from webcompy.di._keys import _COMPONENT_STORE_KEY, _HEAD_PROPS_KEY
        from webcompy.di._scope import _active_di_scope
        from webcompy.ports._keys import ASYNC_SCHEDULER_PORT_KEY, CUSTOM_ELEMENT_PORT_KEY, HOST_PORT_KEY
        from webcompy_testing import FakeBrowserHostPort, FakeCustomElementPort

        dom_port, _, _ = fake_browser_full
        scope = _active_di_scope.get()
        scope.provide(_COMPONENT_STORE_KEY, ComponentStore())
        scope.provide(_HEAD_PROPS_KEY, HeadPropsStore())
        scope.provide(CUSTOM_ELEMENT_PORT_KEY, FakeCustomElementPort())
        scope.provide(HOST_PORT_KEY, FakeBrowserHostPort())
        release = asyncio.Event()

        @define_component()
        async def PendingCmp(context):
            await release.wait()
            return html.DIV({"data-t": "a"}, "resolved")

        b_items = ReactiveList(["b1"])
        teleport_a = Teleport({"to": "body"}, PendingCmp(None))
        teleport_b = Teleport({"to": "body"}, repeat(b_items, lambda item: html.DIV({"data-t": "b"}, item)))
        parent = Element("div", {}, {}, None, None)
        parent._node_cache = FakeDOMNode("div")
        parent._mounted = True

        class _Root:
            def _get_belonging_component(self):
                return ""

            def _get_belonging_components(self):
                return ()

        parent._parent = _Root()
        for idx, teleport in enumerate((teleport_a, teleport_b)):
            teleport._parent = parent
            teleport._node_idx = idx

        def _tags(body):
            tags: list[str] = []
            for i in range(body.childNodes.length):
                node = body.childNodes[i]
                if node.getAttribute("data-t") in ("a", "b"):
                    tags.append((node.getAttribute("data-t") or "") + (node.textContent or ""))
                else:
                    for j in range(node.childNodes.length):
                        inner = node.childNodes[j]
                        if inner.getAttribute("data-t") in ("a", "b"):
                            tags.append((inner.getAttribute("data-t") or "") + (inner.textContent or ""))
            return tags

        task_a = asyncio.create_task(teleport_a._render())
        await asyncio.sleep(0)
        await teleport_b._render()
        assert _tags(dom_port.body) == ["bb1"]
        b_items.append("b2")
        assert _tags(dom_port.body) == ["bb1", "bb2"]
        release.set()
        await task_a
        await inject(ASYNC_SCHEDULER_PORT_KEY).await_pending()
        assert _tags(dom_port.body) == ["aresolved", "bb1", "bb2"]
        b_items.pop(0)
        assert _tags(dom_port.body) == ["aresolved", "bb2"]

    @pytest.mark.asyncio
    async def test_shared_target_count_treats_nested_teleport_with_other_target_as_anchor(
        self, teleport_env, fake_browser_full
    ):
        import asyncio

        from webcompy.components._component import HeadPropsStore
        from webcompy.components._generator import ComponentStore
        from webcompy.di._keys import _COMPONENT_STORE_KEY, _HEAD_PROPS_KEY
        from webcompy.di._scope import _active_di_scope

        dom_port, _, _ = fake_browser_full
        scope = _active_di_scope.get()
        scope.provide(_COMPONENT_STORE_KEY, ComponentStore())
        scope.provide(_HEAD_PROPS_KEY, HeadPropsStore())

        target_a = FakeDOMNode("div")
        target_a.setAttribute("id", "a")
        target_b = FakeDOMNode("div")
        target_b.setAttribute("id", "b")
        dom_port.body.appendChild(target_a)
        dom_port.body.appendChild(target_b)

        inner_items = ReactiveList(["i1", "i2"])
        c_items = ReactiveList(["c1"])

        inner = Teleport({"to": "#b"}, repeat(inner_items, lambda item: html.DIV({"data-t": "inner"}, item)))
        teleport_a = Teleport({"to": "#a"}, inner)
        teleport_c = Teleport({"to": "#a"}, repeat(c_items, lambda item: html.DIV({"data-t": "c"}, item)))

        parent = Element("div", {}, {}, None, None)
        parent._node_cache = FakeDOMNode("div")
        parent._mounted = True

        class _Root:
            def _get_belonging_component(self):
                return ""

            def _get_belonging_components(self):
                return ()

        parent._parent = _Root()
        for idx, teleport in enumerate((teleport_a, teleport_c)):
            teleport._parent = parent
            teleport._node_idx = idx

        def _a_nodes():
            return [
                (target_a.childNodes[i].nodeName, target_a.childNodes[i].textContent or "")
                for i in range(target_a.childNodes.length)
            ]

        def _b_texts():
            return [target_b.childNodes[i].textContent or "" for i in range(target_b.childNodes.length)]

        await teleport_a._render()
        await teleport_c._render()
        await asyncio.sleep(0)

        assert _a_nodes() == [("#comment", "webcompy-teleport-anchor"), ("DIV", "c1")]
        assert _b_texts() == ["i1", "i2"]

        assert inner._node_idx == 0
        assert teleport_c._children[0]._node_idx == 1

        inner_items.append("i3")
        c_items.append("c2")
        assert _a_nodes() == [("#comment", "webcompy-teleport-anchor"), ("DIV", "c1"), ("DIV", "c2")]
        assert _b_texts() == ["i1", "i2", "i3"]


class TestTeleportRemoval:
    def test_conditional_removal_cleans_target_and_anchor(self, teleport_env):
        open_state = Signal(True)

        @define_component()
        def TeleportPage(context):
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

        with TestRenderer.render(TeleportPage) as result:
            body = result.body_node
            assert body is not None
            assert _has_modal(body)
            assert result._root_node.childNodes[0].childNodes.length == 3
            open_state.value = False
            assert not _has_modal(body)
            assert result._root_node.childNodes[0].childNodes.length == 2
            open_state.value = True
            assert _has_modal(body)
            assert result._root_node.childNodes[0].childNodes.length == 3


class TestTeleportReactivity:
    def test_reactive_update_applies_at_target(self, teleport_env):
        message = Signal("initial")

        @define_component()
        def TeleportPage(context):
            return html.DIV({}, Teleport({"to": "body"}, html.SPAN({}, message)))

        with TestRenderer.render(TeleportPage) as result:
            body = result.body_node
            assert body is not None
            spans = _body_children_by_tag(body, "SPAN")
            assert len(spans) == 1
            assert spans[0].textContent == "initial"
            message.value = "updated"
            assert spans[0].textContent == "updated"
            assert result._root_node.childNodes[0].childNodes.length == 1

    def test_scoped_attrs_and_event_handlers_survive_relocation(self, teleport_env):
        clicked: list[int] = []

        @define_component()
        def TeleportModal(context):
            return html.BUTTON({"class": "modal-btn", "@click": lambda ev: clicked.append(1)}, "click me")

        TeleportModal.scoped_style = {" .modal-btn": {"color": "red"}}

        @define_component()
        def TeleportPage(context):
            return html.DIV({}, Teleport({"to": "body"}, TeleportModal(None)))

        with TestRenderer.render(TeleportPage) as result:
            body = result.body_node
            assert body is not None
            wrappers = _body_children_by_tag(body, "TELEPORT-MODAL")
            assert len(wrappers) == 1
            buttons = [
                wrappers[0].childNodes[i]
                for i in range(wrappers[0].childNodes.length)
                if wrappers[0].childNodes[i].nodeName == "BUTTON"
            ]
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
        prerendered_anchor = FakeDOMNode("#comment", text_content="webcompy-teleport-anchor")
        prerendered_anchor.__webcompy_prerendered_node__ = True
        parent._node_cache.appendChild(prerendered_anchor)

        teleport = Teleport({"to": "body"}, Element("span", {}, {}, None, [TextElement("teleported")]))
        teleport._parent = parent
        teleport._node_idx = 0
        teleport._hydrate_node()
        assert teleport._node_cache is prerendered_anchor
        assert teleport._mounted is True
        assert (prerendered_anchor.textContent or "") == "webcompy-teleport-anchor"

        await inject(ASYNC_SCHEDULER_PORT_KEY).await_pending()
        body = dom_port.body
        spans = [body.childNodes[i] for i in range(body.childNodes.length) if body.childNodes[i].nodeName == "SPAN"]
        assert len(spans) == 1
        assert spans[0].textContent == "teleported"


class TestTeleportSSR:
    def test_ssr_emits_content_under_body_by_default(self):
        @define_component()
        def TeleportPage(context):
            return html.DIV(
                {},
                html.P({}, "before-marker"),
                Teleport({"to": "body"}, html.DIV({"id": "ssr-modal"}, "MODAL-SECRET")),
                html.P({}, "after-marker"),
            )

        app = create_test_app(root_component=TeleportPage)
        html_str = render_app_html(
            app,
            app_package_name="test_pkg",
            dev_mode=False,
            prerender=True,
            wheel_filename="test_pkg-0+sha.abcdef12-py3-none-any.whl",
        )
        assert "<!--wc-teleport-block:0:body-->" in html_str
        assert '<div id="ssr-modal"' in html_str
        assert "MODAL-SECRET" in html_str
        assert html_str.index("<!--wc-teleport-block:0:body-->") > html_str.index('id="webcompy-app"')
        block_end_index = html_str.index("<!--wc-teleport-block-end:0-->")
        assert block_end_index < html_str.index("</body>")
        assert "<!--webcompy-teleport-anchor-->" in html_str
        assert "\u200b" not in html_str

    def test_ssr_opt_out_emits_anchor_only(self):
        @define_component()
        def TeleportPage(context):
            return html.DIV(
                {},
                html.P({}, "before-marker"),
                Teleport({"to": "body", "ssr": False}, html.DIV({"id": "ssr-modal"}, "MODAL-SECRET")),
                html.P({}, "after-marker"),
            )

        app = create_test_app(root_component=TeleportPage)
        html_str = render_app_html(
            app,
            app_package_name="test_pkg",
            dev_mode=False,
            prerender=True,
            wheel_filename="test_pkg-0+sha.abcdef12-py3-none-any.whl",
        )
        assert "MODAL-SECRET" not in html_str
        assert 'id="ssr-modal"' not in html_str
        assert "<!--wc-teleport-block:" not in html_str
        assert "<!--webcompy-teleport-anchor-->" in html_str
        assert "before-marker" in html_str
        assert "after-marker" in html_str

    def test_ssr_unresolvable_target_falls_back_to_anchor_only(self, caplog):
        import logging as _logging

        @define_component()
        def TeleportPage(context):
            return html.DIV(
                {},
                Teleport({"to": "#nowhere-container"}, html.DIV({}, "orphan-content")),
            )

        app = create_test_app(root_component=TeleportPage)
        with caplog.at_level(_logging.WARNING, logger="webcompy_server._teleport_emission"):
            html_str = render_app_html(
                app,
                app_package_name="test_pkg",
                dev_mode=False,
                prerender=True,
                wheel_filename="test_pkg-0+sha.abcdef12-py3-none-any.whl",
            )
        assert any("nowhere-container" in record.getMessage() for record in caplog.records)
        assert "orphan-content" not in html_str
        assert "<!--wc-teleport-block:" not in html_str
        assert "<!--webcompy-teleport-anchor-->" in html_str

    def test_ssr_app_subtree_target_is_rejected(self, caplog):
        import logging as _logging

        @define_component()
        def TeleportPage(context):
            return html.DIV(
                {},
                html.DIV({"id": "inner-root"}),
                Teleport({"to": "#inner-root"}, html.DIV({}, "inner-content")),
            )

        app = create_test_app(root_component=TeleportPage)
        with caplog.at_level(_logging.WARNING, logger="webcompy_server._teleport_emission"):
            html_str = render_app_html(
                app,
                app_package_name="test_pkg",
                dev_mode=False,
                prerender=True,
                wheel_filename="test_pkg-0+sha.abcdef12-py3-none-any.whl",
            )
        assert any("inner-root" in record.getMessage() for record in caplog.records)
        assert "inner-content" not in html_str
        assert "<!--wc-teleport-block:" not in html_str
        assert "<!--webcompy-teleport-anchor-->" in html_str

    def test_ssr_rejects_selector_with_unsupported_syntax(self, caplog):
        import logging as _logging

        @define_component()
        def TeleportPage(context):
            return html.DIV(
                {},
                Teleport({"to": "div[attr=x]"}, html.DIV({}, "attr-content")),
            )

        app = create_test_app(root_component=TeleportPage)
        with caplog.at_level(_logging.WARNING, logger="webcompy_server._teleport_emission"):
            html_str = render_app_html(
                app,
                app_package_name="test_pkg",
                dev_mode=False,
                prerender=True,
                wheel_filename="test_pkg-0+sha.abcdef12-py3-none-any.whl",
            )
        assert any("unsupported selector syntax" in record.getMessage() for record in caplog.records)
        assert "attr-content" not in html_str

    def test_ssr_repeated_children_emit_n_items(self):
        from webcompy.signal import ReactiveList

        items = ReactiveList(["a", "b", "c"])

        @define_component()
        def TeleportPage(context):
            return html.DIV(
                {},
                Teleport({"to": "body"}, repeat(items, lambda item: html.LI({}, item))),
            )

        app = create_test_app(root_component=TeleportPage)
        html_str = render_app_html(
            app,
            app_package_name="test_pkg",
            dev_mode=False,
            prerender=True,
            wheel_filename="test_pkg-0+sha.abcdef12-py3-none-any.whl",
        )
        block_start = html_str.index("<!--wc-teleport-block:0:")
        block_end = html_str.index("<!--wc-teleport-block-end:0-->")
        block = html_str[block_start:block_end]
        assert block.count("<li") == 3

    def test_ssr_async_child_settles_before_serialization(self):
        @define_component()
        async def AsyncInner(context):
            await asyncio.sleep(0)
            return html.DIV({"id": "async-child"}, "async-resolved")

        @define_component()
        def TeleportPage(context):
            return html.DIV(
                {},
                Teleport({"to": "body"}, AsyncInner(None)),
            )

        app = create_test_app(root_component=TeleportPage)
        html_str = render_app_html(
            app,
            app_package_name="test_pkg",
            dev_mode=False,
            prerender=True,
            wheel_filename="test_pkg-0+sha.abcdef12-py3-none-any.whl",
        )
        assert "<!--wc-teleport-block:0:body-->" in html_str
        assert "async-resolved" in html_str

    def test_ssr_teleported_component_signal_is_transferred(self):
        from webcompy.signal import use_state

        @define_component()
        def InnerComponent(context):
            label = use_state(lambda: "transfer-secret")
            return html.SPAN({}, label)

        @define_component()
        def TeleportPage(context):
            return html.DIV(
                {},
                Teleport({"to": "body"}, InnerComponent(None)),
            )

        app = create_test_app(root_component=TeleportPage)
        html_str = render_app_html(
            app,
            app_package_name="test_pkg",
            dev_mode=False,
            prerender=True,
            wheel_filename="test_pkg-0+sha.abcdef12-py3-none-any.whl",
        )
        data_start = html_str.index("__webcompy_data__")
        data_section = html_str[data_start : html_str.index("</script>", data_start)]
        assert "transfer-secret" in data_section

    def test_ssr_nested_teleport_gets_next_ordinal_and_anchor(self):
        @define_component()
        def InnerComp(context):
            return html.DIV({}, Teleport({"to": "body"}, html.SPAN({}, "nested")))

        @define_component()
        def TeleportPage(context):
            return html.DIV({}, Teleport({"to": "body"}, InnerComp(None)))

        app = create_test_app(root_component=TeleportPage)
        html_str = render_app_html(
            app,
            app_package_name="test_pkg",
            dev_mode=False,
            prerender=True,
            wheel_filename="test_pkg-0+sha.abcdef12-py3-none-any.whl",
        )
        assert "<!--wc-teleport-block:0:body-->" in html_str
        assert "<!--wc-teleport-block:1:body-->" in html_str
        outer_anchor_in_subtree = html_str.index("<!--webcompy-teleport-anchor-->") < html_str.index(
            "<!--wc-teleport-block:0:"
        )
        del outer_anchor_in_subtree
        nested_start = html_str.index("<!--wc-teleport-block:1:body-->")
        outer_end = html_str.index("<!--wc-teleport-block-end:0-->")
        assert nested_start > outer_end
        assert "nested" in html_str

    @pytest.mark.asyncio
    async def test_ssr_render_mounts_anchor_only(self, server_di_scope):
        from tests.conftest import FakeDOMNode

        el = TeleportElement({"to": "body"}, Element("span", {}, {}, None, [TextElement("secret")]))
        parent = Element("div")
        parent._node_cache = FakeDOMNode("div")
        parent._mounted = True
        el._parent = parent
        el._node_idx = 0
        await el._render()
        parent_node = parent._get_node()
        assert parent_node.childNodes.length == 1
        assert parent_node.childNodes[0].nodeName == "#comment"
        assert (parent_node.childNodes[0].textContent or "") == "webcompy-teleport-anchor"
        assert el._children[0]._node_cache is None

    def test_ssr_anchor_emits_comment_without_zero_width_space(self):
        @define_component()
        def TeleportPage(context):
            return html.DIV(
                {},
                html.LI(
                    {"class": "navbar-item-dropdown"},
                    html.A({}, "Documents"),
                    Teleport({"to": "body"}, html.UL({}, html.LI({}, "item"))),
                ),
            )

        app = create_test_app(root_component=TeleportPage)
        html_str = render_app_html(
            app,
            app_package_name="test_pkg",
            dev_mode=False,
            prerender=True,
            wheel_filename="test_pkg-0+sha.abcdef12-py3-none-any.whl",
        )
        assert "<!--webcompy-teleport-anchor-->" in html_str
        assert "\u200b" not in html_str


class _FakeDOMParser(HTMLParser):
    _VOID_TAGS = frozenset(
        {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}
    )

    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self.root: FakeDOMNode | None = None
        self._stack: list[FakeDOMNode] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        node = FakeDOMNode(tag)
        for name, value in attrs:
            node.setAttribute(name, value if value is not None else "")
        if self._stack:
            self._stack[-1].appendChild(node)
        else:
            self.root = node
        if tag not in self._VOID_TAGS:
            self._stack.append(node)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag: str) -> None:
        if self._stack:
            self._stack.pop()

    def handle_comment(self, data: str) -> None:
        if self._stack:
            self._stack[-1].appendChild(FakeDOMNode("#comment", text_content=data))

    def handle_data(self, data: str) -> None:
        if self._stack:
            self._stack[-1].appendChild(FakeDOMNode("#text", text_content=data))


def _find_by_id(node: FakeDOMNode, element_id: str) -> FakeDOMNode | None:
    if node.getAttribute("id") == element_id:
        return node
    for i in range(node.childNodes.length):
        result = _find_by_id(node.childNodes[i], element_id)
        if result is not None:
            return result
    return None


def _mark_prerendered(node: FakeDOMNode) -> None:
    node.__webcompy_prerendered_node__ = True
    for i in range(node.childNodes.length):
        _mark_prerendered(node.childNodes[i])


class TestTeleportSSRHydrationRoundTrip:
    @pytest.mark.asyncio
    async def test_hydration_after_ssr_keeps_siblings_single_and_adopts_anchor(self, monkeypatch, fake_browser_full):
        from webcompy.di import inject
        from webcompy.ports._keys import ASYNC_SCHEDULER_PORT_KEY

        dom_port, _, _ = fake_browser_full

        @define_component()
        def TeleportPage(context):
            return html.DIV(
                {},
                html.P({"data-testid": "before"}, "before-marker"),
                Teleport({"to": "body"}, html.DIV({"id": "modal"}, "MODAL-SECRET")),
                html.P({"data-testid": "after"}, "after-marker"),
            )

        app = create_test_app(root_component=TeleportPage)
        html_str = render_app_html(
            app,
            app_package_name="test_pkg",
            dev_mode=False,
            prerender=True,
            wheel_filename="test_pkg-0+sha.abcdef12-py3-none-any.whl",
        )
        assert "<!--webcompy-teleport-anchor-->" in html_str
        parser = _FakeDOMParser()
        parser.feed(html_str)
        parser.close()
        assert parser.root is not None
        app_div = _find_by_id(parser.root, "webcompy-app")
        assert app_div is not None
        page_div = app_div.childNodes[0].childNodes[0]
        assert page_div.childNodes.length == 3
        _mark_prerendered(page_div)
        dom_port._body.appendChild(page_div)

        monkeypatch.setattr("webcompy.elements.types._teleport.ENVIRONMENT", "pyscript")

        p_before = Element("p", {"data-testid": "before"}, {}, None, [TextElement("before-marker")])
        teleport = Teleport({"to": "body"}, Element("div", {"id": "modal"}, {}, None, [TextElement("MODAL-SECRET")]))
        p_after = Element("p", {"data-testid": "after"}, {}, None, [TextElement("after-marker")])
        div = Element("div", {}, {}, None, None)
        div._children = [p_before, teleport, p_after]
        div._node_cache = page_div
        div._mounted = True
        for idx, child in enumerate(div._children):
            child._parent = div
            child._node_idx = idx

        class _PageRoot:
            def _get_belonging_component(self):
                return ""

            def _get_belonging_components(self):
                return ()

        div._parent = _PageRoot()

        for child in div._children:
            child._hydrate_node()
        for child in div._children:
            await child._render()
        await inject(ASYNC_SCHEDULER_PORT_KEY).await_pending()

        children = [page_div.childNodes[i] for i in range(page_div.childNodes.length)]
        assert [child.nodeName for child in children] == ["P", "#comment", "P"]
        assert children[1] is teleport._node_cache
        assert getattr(children[1], "__webcompy_prerendered_node__", False) is True
        after_markers = [child for child in children if child.getAttribute("data-testid") == "after"]
        assert len(after_markers) == 1
        assert children[2] is after_markers[0]
        assert getattr(children[2], "__webcompy_prerendered_node__", False) is True
        body_children = [dom_port._body.childNodes[i] for i in range(dom_port._body.childNodes.length)]
        modals = [child for child in body_children if child.getAttribute("id") == "modal"]
        assert len(modals) == 1
        assert modals[0].textContent == "MODAL-SECRET"

    @pytest.mark.asyncio
    async def test_hydration_with_bare_text_siblings_adopts_comment_anchor_in_order(
        self, monkeypatch, fake_browser_full
    ):
        from webcompy.di import inject
        from webcompy.ports._keys import ASYNC_SCHEDULER_PORT_KEY

        dom_port, _, _ = fake_browser_full

        @define_component()
        def TeleportPage(context):
            return html.DIV(
                {},
                "before-marker",
                Teleport({"to": "body"}, html.DIV({"id": "modal"}, "MODAL-SECRET")),
                "after-marker",
            )

        app = create_test_app(root_component=TeleportPage)
        html_str = render_app_html(
            app,
            app_package_name="test_pkg",
            dev_mode=False,
            prerender=True,
            wheel_filename="test_pkg-0+sha.abcdef12-py3-none-any.whl",
        )
        assert "<!--webcompy-teleport-anchor-->" in html_str
        parser = _FakeDOMParser()
        parser.feed(html_str)
        parser.close()
        assert parser.root is not None
        app_div = _find_by_id(parser.root, "webcompy-app")
        assert app_div is not None
        page_div = app_div.childNodes[0].childNodes[0]
        assert page_div.childNodes.length == 3
        parsed = [page_div.childNodes[i] for i in range(page_div.childNodes.length)]
        assert [child.nodeName for child in parsed] == ["#text", "#comment", "#text"]
        assert parsed[0].textContent == "before-marker"
        assert parsed[1].textContent == "webcompy-teleport-anchor"
        assert parsed[2].textContent == "after-marker"
        _mark_prerendered(page_div)
        dom_port._body.appendChild(page_div)

        monkeypatch.setattr("webcompy.elements.types._teleport.ENVIRONMENT", "pyscript")

        text_before = TextElement("before-marker")
        teleport = Teleport({"to": "body"}, Element("div", {"id": "modal"}, {}, None, [TextElement("MODAL-SECRET")]))
        text_after = TextElement("after-marker")
        div = Element("div", {}, {}, None, None)
        div._children = [text_before, teleport, text_after]
        div._node_cache = page_div
        div._mounted = True
        for idx, child in enumerate(div._children):
            child._parent = div
            child._node_idx = idx

        class _PageRoot:
            def _get_belonging_component(self):
                return ""

            def _get_belonging_components(self):
                return ()

        div._parent = _PageRoot()

        for child in div._children:
            child._hydrate_node()
        for child in div._children:
            await child._render()
        await inject(ASYNC_SCHEDULER_PORT_KEY).await_pending()

        children = [page_div.childNodes[i] for i in range(page_div.childNodes.length)]
        assert [child.nodeName for child in children] == ["#text", "#comment", "#text"]
        assert children[0].textContent == "before-marker"
        assert children[1] is teleport._node_cache
        assert getattr(children[1], "__webcompy_prerendered_node__", False) is True
        assert (children[1].textContent or "") == "webcompy-teleport-anchor"
        assert children[2].textContent == "after-marker"
        before_markers = [child for child in children if (child.textContent or "") == "before-marker"]
        after_markers = [child for child in children if (child.textContent or "") == "after-marker"]
        assert len(before_markers) == 1
        assert len(after_markers) == 1
        body_children = [dom_port._body.childNodes[i] for i in range(dom_port._body.childNodes.length)]
        modals = [child for child in body_children if child.getAttribute("id") == "modal"]
        assert len(modals) == 1
        assert modals[0].textContent == "MODAL-SECRET"

    @pytest.mark.asyncio
    async def test_fresh_anchor_teleport_schedules_own_render_during_hydration(self, monkeypatch, fake_browser_full):
        from webcompy.di import inject
        from webcompy.ports._keys import ASYNC_SCHEDULER_PORT_KEY

        dom_port, _, _ = fake_browser_full

        @define_component()
        def TeleportPage(context):
            return html.DIV(
                {},
                "before-marker",
                Teleport({"to": "body"}, html.DIV({"id": "modal"}, "MODAL-SECRET")),
                "after-marker",
            )

        app = create_test_app(root_component=TeleportPage)
        html_str = render_app_html(
            app,
            app_package_name="test_pkg",
            dev_mode=False,
            prerender=True,
            wheel_filename="test_pkg-0+sha.abcdef12-py3-none-any.whl",
        )
        parser = _FakeDOMParser()
        parser.feed(html_str)
        parser.close()
        assert parser.root is not None
        app_div = _find_by_id(parser.root, "webcompy-app")
        assert app_div is not None
        page_div = app_div.childNodes[0].childNodes[0]
        assert page_div.childNodes.length == 3
        parsed = [page_div.childNodes[i] for i in range(page_div.childNodes.length)]
        assert [child.nodeName for child in parsed] == ["#text", "#comment", "#text"]
        comment_anchor = parsed[1]
        comment_anchor.remove()
        assert page_div.childNodes.length == 2
        _mark_prerendered(page_div)
        dom_port._body.appendChild(page_div)

        monkeypatch.setattr("webcompy.elements.types._teleport.ENVIRONMENT", "pyscript")

        text_before = TextElement("before-marker")
        teleport = Teleport({"to": "body"}, Element("div", {"id": "modal"}, {}, None, [TextElement("MODAL-SECRET")]))
        text_after = TextElement("after-marker")
        div = Element("div", {}, {}, None, None)
        div._children = [text_before, teleport, text_after]
        div._node_cache = page_div
        div._mounted = True
        for idx, child in enumerate(div._children):
            child._parent = div
            child._node_idx = idx

        class _PageRoot:
            def _get_belonging_component(self):
                return ""

            def _get_belonging_components(self):
                return ()

        div._parent = _PageRoot()

        for child in div._children:
            child._hydrate_node()
        for child in div._children:
            await child._render()
        await inject(ASYNC_SCHEDULER_PORT_KEY).await_pending()

        assert teleport._mounted is True
        assert teleport._children_rendered is True
        children = [page_div.childNodes[i] for i in range(page_div.childNodes.length)]
        assert [child.nodeName for child in children] == ["#text", "#comment", "#text"]
        assert children[0].textContent == "before-marker"
        assert children[1] is teleport._node_cache
        assert (children[1].textContent or "") == "webcompy-teleport-anchor"
        assert children[2].textContent == "after-marker"
        before_markers = [child for child in children if (child.textContent or "") == "before-marker"]
        after_markers = [child for child in children if (child.textContent or "") == "after-marker"]
        assert len(before_markers) == 1
        assert len(after_markers) == 1
        body_children = [dom_port._body.childNodes[i] for i in range(dom_port._body.childNodes.length)]
        modals = [child for child in body_children if child.getAttribute("id") == "modal"]
        assert len(modals) == 1
        assert modals[0].textContent == "MODAL-SECRET"

    @pytest.mark.asyncio
    async def test_hydration_with_stripped_comment_merges_text_and_recovers(self, monkeypatch, fake_browser_full):
        from webcompy.di import inject
        from webcompy.ports._keys import ASYNC_SCHEDULER_PORT_KEY

        dom_port, _, _ = fake_browser_full

        @define_component()
        def TeleportPage(context):
            return html.DIV(
                {},
                "before-marker",
                Teleport({"to": "body"}, html.DIV({"id": "modal"}, "MODAL-SECRET")),
                "after-marker",
            )

        app = create_test_app(root_component=TeleportPage)
        html_str = render_app_html(
            app,
            app_package_name="test_pkg",
            dev_mode=False,
            prerender=True,
            wheel_filename="test_pkg-0+sha.abcdef12-py3-none-any.whl",
        )
        assert "<!--webcompy-teleport-anchor-->" in html_str
        html_str = html_str.replace("<!--webcompy-teleport-anchor-->", "")
        parser = _FakeDOMParser()
        parser.feed(html_str)
        parser.close()
        assert parser.root is not None
        app_div = _find_by_id(parser.root, "webcompy-app")
        assert app_div is not None
        page_div = app_div.childNodes[0].childNodes[0]
        assert page_div.childNodes.length == 1
        assert page_div.childNodes[0].nodeName == "#text"
        assert page_div.childNodes[0].textContent == "before-markerafter-marker"
        _mark_prerendered(page_div)
        dom_port._body.appendChild(page_div)

        monkeypatch.setattr("webcompy.elements.types._teleport.ENVIRONMENT", "pyscript")

        text_before = TextElement("before-marker")
        teleport = Teleport({"to": "body"}, Element("div", {"id": "modal"}, {}, None, [TextElement("MODAL-SECRET")]))
        text_after = TextElement("after-marker")
        div = Element("div", {}, {}, None, None)
        div._children = [text_before, teleport, text_after]
        div._node_cache = page_div
        div._mounted = True
        for idx, child in enumerate(div._children):
            child._parent = div
            child._node_idx = idx

        class _PageRoot:
            def _get_belonging_component(self):
                return ""

            def _get_belonging_components(self):
                return ()

        div._parent = _PageRoot()

        for child in div._children:
            child._hydrate_node()
        for child in div._children:
            await child._render()
        await inject(ASYNC_SCHEDULER_PORT_KEY).await_pending()

        children = [page_div.childNodes[i] for i in range(page_div.childNodes.length)]
        assert [child.nodeName for child in children] == ["#text", "#comment", "#text"]
        assert children[0].textContent == "before-marker"
        assert children[1] is teleport._node_cache
        assert (children[1].textContent or "") == "webcompy-teleport-anchor"
        assert children[2].textContent == "after-marker"
        before_markers = [child for child in children if (child.textContent or "") == "before-marker"]
        after_markers = [child for child in children if (child.textContent or "") == "after-marker"]
        assert len(before_markers) == 1
        assert len(after_markers) == 1
        body_children = [dom_port._body.childNodes[i] for i in range(dom_port._body.childNodes.length)]
        modals = [child for child in body_children if child.getAttribute("id") == "modal"]
        assert len(modals) == 1
        assert modals[0].textContent == "MODAL-SECRET"

    def _install_manual_block(self, dom_port, ordinal: int, selector: str, child_id: str, text: str):
        start = dom_port.create_comment(f"wc-teleport-block:{ordinal}:{selector}")
        content = dom_port.create_element("div")
        content.setAttribute("id", child_id)
        content.appendChild(dom_port.create_text_node(text))
        end = dom_port.create_comment(f"wc-teleport-block-end:{ordinal}")
        for node in (start, content, end):
            node.__webcompy_prerendered_node__ = True
            dom_port._body.appendChild(node)
        return content

    def _body_marker_datas(self, dom_port) -> list[str]:
        return [
            (dom_port._body.childNodes[i].textContent or "")
            for i in range(dom_port._body.childNodes.length)
            if dom_port._body.childNodes[i].nodeName == "#comment"
            and str(dom_port._body.childNodes[i].textContent or "").startswith("wc-teleport-block")
        ]

    def _make_prerendered_page(self, dom_port):
        page_div = FakeDOMNode("div")
        page_div.setAttribute("id", "webcompy-page-root")
        anchor_comment = FakeDOMNode("#comment", text_content="webcompy-teleport-anchor")
        page_div.appendChild(anchor_comment)
        _mark_prerendered(page_div)
        dom_port._body.appendChild(page_div)
        return page_div

    def _build_hydration_pair(self, monkeypatch, dom_port, page_div, props: dict, child_id: str, text: str):
        monkeypatch.setattr("webcompy.elements.types._teleport.ENVIRONMENT", "pyscript")
        teleport = Teleport(props, Element("div", {"id": child_id}, {}, None, [TextElement(text)]))
        wrapper = Element("div", {}, {}, None, None)
        wrapper._node_cache = page_div
        wrapper._mounted = True
        teleport._parent = wrapper
        teleport._node_idx = 0
        return teleport

    @pytest.mark.asyncio
    async def test_hydration_claims_emitted_block_exactly_once(self, monkeypatch, fake_browser_full):
        from webcompy.di import inject
        from webcompy.ports._keys import ASYNC_SCHEDULER_PORT_KEY

        dom_port, _, _ = fake_browser_full
        self._install_manual_block(dom_port, 0, "body", "modal", "MODAL-SECRET")
        page_div = self._make_prerendered_page(dom_port)

        teleport = self._build_hydration_pair(monkeypatch, dom_port, page_div, {"to": "body"}, "modal", "MODAL-SECRET")
        teleport._hydrate_node()
        await teleport._render()
        await inject(ASYNC_SCHEDULER_PORT_KEY).await_pending()

        assert self._body_marker_datas(dom_port) == []
        modals = [
            dom_port._body.childNodes[i]
            for i in range(dom_port._body.childNodes.length)
            if dom_port._body.childNodes[i].getAttribute("id") == "modal"
        ]
        assert len(modals) == 1
        assert modals[0].textContent == "MODAL-SECRET"
        assert getattr(teleport._node_cache, "__webcompy_prerendered_node__", False) is True

    @pytest.mark.asyncio
    async def test_shared_target_blocks_claimed_by_matching_ordinals(self, monkeypatch, fake_browser_full):
        from webcompy.di import inject
        from webcompy.ports._keys import ASYNC_SCHEDULER_PORT_KEY

        dom_port, _, _ = fake_browser_full
        self._install_manual_block(dom_port, 0, "body", "modal-a", "CONTENT-A")
        self._install_manual_block(dom_port, 1, "body", "modal-b", "CONTENT-B")
        page_div = self._make_prerendered_page(dom_port)

        monkeypatch.setattr("webcompy.elements.types._teleport.ENVIRONMENT", "pyscript")

        page_root = Element("div", {}, {}, None, None)
        page_root._node_cache = page_div
        page_root._mounted = True

        class _PageRoot:
            def _get_belonging_component(self):
                return ""

            def _get_belonging_components(self):
                return ()

        page_root._parent = _PageRoot()

        teleport_a = Teleport({"to": "body"}, Element("div", {"id": "modal-a"}, {}, None, [TextElement("CONTENT-A")]))
        teleport_a._parent = page_root
        teleport_a._node_idx = 0
        teleport_b = Teleport({"to": "body"}, Element("div", {"id": "modal-b"}, {}, None, [TextElement("CONTENT-B")]))
        teleport_b._parent = page_root
        teleport_b._node_idx = 1

        teleport_a._hydrate_node()
        teleport_b._hydrate_node()
        await teleport_a._render()
        await teleport_b._render()
        await inject(ASYNC_SCHEDULER_PORT_KEY).await_pending()

        assert self._body_marker_datas(dom_port) == []
        modal_ids = [dom_port._body.childNodes[i].getAttribute("id") for i in range(dom_port._body.childNodes.length)]
        modal_ids = [k for k in modal_ids if k in ("modal-a", "modal-b")]
        assert sorted(modal_ids) == ["modal-a", "modal-b"]

    @pytest.mark.asyncio
    async def test_stale_html_falls_back_with_warning_and_single_copy(self, monkeypatch, fake_browser_full, caplog):
        import logging as _logging

        from webcompy.di import inject
        from webcompy.ports._keys import ASYNC_SCHEDULER_PORT_KEY

        dom_port, _, _ = fake_browser_full
        page_div = self._make_prerendered_page(dom_port)

        teleport = self._build_hydration_pair(monkeypatch, dom_port, page_div, {"to": "body"}, "modal", "MODAL-SECRET")
        with caplog.at_level(_logging.WARNING, logger="webcompy"):
            teleport._hydrate_node()
            await teleport._render()
        await inject(ASYNC_SCHEDULER_PORT_KEY).await_pending()

        assert any(
            "not found" in record.getMessage() and "mounting via client render" in record.getMessage()
            for record in caplog.records
        )
        assert self._body_marker_datas(dom_port) == []
        modals = [
            dom_port._body.childNodes[i]
            for i in range(dom_port._body.childNodes.length)
            if dom_port._body.childNodes[i].getAttribute("id") == "modal"
        ]
        assert len(modals) == 1

    @pytest.mark.asyncio
    async def test_destroyed_before_claim_sweeps_unconsumed_block(self, monkeypatch, fake_browser_full):
        dom_port, _, _ = fake_browser_full
        self._install_manual_block(dom_port, 0, "body", "modal", "MODAL-SECRET")
        page_div = self._make_prerendered_page(dom_port)

        teleport = self._build_hydration_pair(monkeypatch, dom_port, page_div, {"to": "body"}, "modal", "MODAL-SECRET")
        teleport._hydrate_node()
        teleport._remove_element(True, True)

        assert self._body_marker_datas(dom_port) == []
        modals = [
            dom_port._body.childNodes[i]
            for i in range(dom_port._body.childNodes.length)
            if dom_port._body.childNodes[i].getAttribute("id") == "modal"
        ]
        assert modals == []
