from __future__ import annotations

import asyncio
from contextlib import contextmanager
from typing import Any

from tests.conftest import FakeDOMNode, MockHistoryPort
from webcompy import use_computed, use_reactive_dict, use_reactive_list, use_state
from webcompy.components import ComponentContext, define_component
from webcompy.components._component import Component, HeadPropsStore
from webcompy.di import DIScope
from webcompy.di._keys import _HEAD_PROPS_KEY, _ROUTER_KEY
from webcompy.di._scope import _active_di_scope
from webcompy.elements import html, raw_html
from webcompy.elements.types._element import Element
from webcompy.elements.types._fragment import FragmentElement
from webcompy.elements.types._repeat import MultiLineTextElement
from webcompy.elements.types._switch import SwitchElement
from webcompy.elements.types._text import RawHTMLElement, TextElement
from webcompy.hydration._collect import _collect_component_signals
from webcompy.ports._keys import (
    ASYNC_SCHEDULER_PORT_KEY,
    DOM_PORT_KEY,
    FFI_PORT_KEY,
    HOST_PORT_KEY,
    MARKDOWN_PORT_KEY,
)
from webcompy.router import Router, RouterLink, RouterView
from webcompy.router._pages import RouterPage
from webcompy.signal import Computed, ReactiveList, Signal, readonly
from webcompy.signal._computed import _OwnedComputed
from webcompy.signal._container import SignalReceivable
from webcompy.template import render_markdown, render_template
from webcompy.template._cache import clear_cache
from webcompy.template._markdown_default import DefaultMarkdownParser
from webcompy.template._markdown_for import MarkdownForElement
from webcompy_testing import (
    FakeAsyncSchedulerPort,
    FakeBrowserDOMPort,
    FakeBrowserFFIPort,
    FakeBrowserHostPort,
    TestRenderer,
)


def _active_consumer_count(node: Any) -> int:
    count = 0
    edge = getattr(node, "consumers", None)
    while edge is not None:
        if edge.active:
            count += 1
        edge = edge.next_consumer
    return count


class _FakeRootElement(Element):
    def _get_belonging_component(self) -> str:
        return ""

    def _get_belonging_components(self) -> tuple[()]:
        return ()


def _make_mounted_parent() -> _FakeRootElement:
    parent = _FakeRootElement("div", {}, {}, None, None)
    parent._node_cache = FakeDOMNode("div")
    parent._mounted = True
    return parent


@contextmanager
def _markdown_scope() -> Any:
    clear_cache()
    dom_port = FakeBrowserDOMPort()
    scope = DIScope()
    scope.provide(DOM_PORT_KEY, dom_port)
    scope.provide(HOST_PORT_KEY, FakeBrowserHostPort(dom_port))
    scope.provide(FFI_PORT_KEY, FakeBrowserFFIPort())
    scope.provide(ASYNC_SCHEDULER_PORT_KEY, FakeAsyncSchedulerPort())
    scope.provide(MARKDOWN_PORT_KEY, DefaultMarkdownParser())
    token = _active_di_scope.set(scope)
    try:
        yield scope
    finally:
        _active_di_scope.reset(token)
        scope.dispose()
        clear_cache()


class TestRepeatElementCallerSignalPreservation:
    def test_repeat_over_caller_computed_survives_conditional_unmount_and_remount(self) -> None:
        items_holder: dict[str, Any] = {}

        @define_component()
        def FilteredUsers(context: ComponentContext[None]):
            query = use_state(lambda: "")
            users = use_reactive_list(lambda: ["Alice", "Bob", "Carol"])
            filtered = use_computed(
                lambda: (
                    [u for u in users.value if query.value.lower() in u.lower()] if query.value else list(users.value)
                )
            )
            items_holder["query"] = query
            items_holder["users"] = users
            items_holder["filtered"] = filtered
            return render_template(
                "<div>{% if filtered %}<ul>{% for u in filtered %}<li>{{ u }}</li>{% endfor %}</ul>"
                "{% else %}<p>empty</p>{% endif %}</div>",
                {"filtered": filtered},
            )

        res = TestRenderer.render(FilteredUsers)
        try:
            assert [li.textContent for li in res.query_selector_all("li")] == ["Alice", "Bob", "Carol"]

            items_holder["query"].value = "zzz"
            assert res.query_selector_all("li") == []
            assert res.query_selector("p") is not None
            assert items_holder["filtered"].producers is not None

            items_holder["query"].value = ""
            assert items_holder["filtered"].value == ["Alice", "Bob", "Carol"]
            assert [li.textContent for li in res.query_selector_all("li")] == ["Alice", "Bob", "Carol"]

            items_holder["query"].value = "Ali"
            assert [li.textContent for li in res.query_selector_all("li")] == ["Alice"]
        finally:
            res.close()

    def test_repeat_over_caller_reactive_list_and_dict_survive_unmount(self) -> None:
        state_holder: dict[str, Any] = {}

        @define_component()
        def ToggleCollections(context: ComponentContext[None]):
            show = use_state(lambda: True)
            items = use_reactive_list(lambda: ["x"])
            mapping = use_reactive_dict(lambda: {"k": "v1"})
            state_holder["show"] = show
            state_holder["items"] = items
            state_holder["mapping"] = mapping
            return render_template(
                "<div>{% if show %}"
                "<ul>{% for x in items %}<li>{{ x }}</li>{% endfor %}</ul>"
                "<dl>{% for k, v in mapping %}<dd>{{ k }}={{ v }}</dd>{% endfor %}</dl>"
                "{% endif %}</div>",
                {"show": show, "items": items, "mapping": mapping},
            )

        res = TestRenderer.render(ToggleCollections)
        try:
            assert [el.textContent for el in res.query_selector_all("li")] == ["x"]
            assert [el.textContent for el in res.query_selector_all("dd")] == ["k=v1"]

            state_holder["show"].value = False
            assert res.query_selector_all("li") == []
            assert _active_consumer_count(state_holder["items"]) == 0
            assert _active_consumer_count(state_holder["mapping"]) == 0

            state_holder["items"].append("y")
            state_holder["mapping"]["k"] = "v2"
            state_holder["show"].value = True
            assert [el.textContent for el in res.query_selector_all("li")] == ["x", "y"]
            assert [el.textContent for el in res.query_selector_all("dd")] == ["k=v2"]
        finally:
            res.close()


class TestTextAndRawHtmlCallerSignalPreservation:
    def test_text_element_caller_computed_and_readonly_survive_unmount(self) -> None:
        refs: dict[str, Any] = {}

        @define_component()
        def ConditionalText(context: ComponentContext[None]):
            show = use_state(lambda: True)
            count = use_state(lambda: 1)
            doubled = use_computed(lambda: count.value * 2)
            ro = readonly(doubled)
            refs["show"] = show
            refs["count"] = count
            refs["doubled"] = doubled
            refs["ro"] = ro
            return render_template(
                "<div>{% if show %}<span class='a'>{{ doubled }}</span>"
                "<span class='b'>{{ ro }}</span>{% else %}<p>off</p>{% endif %}</div>",
                {"show": show, "doubled": doubled, "ro": ro},
            )

        res = TestRenderer.render(ConditionalText)
        try:
            spans = res.query_selector_all("span")
            assert [s.textContent for s in spans] == ["2", "2"]

            refs["show"].value = False
            assert refs["doubled"].producers is not None
            assert refs["ro"].producers is not None

            refs["count"].value = 5
            assert refs["doubled"].value == 10
            assert refs["ro"].value == 10

            refs["show"].value = True
            assert [s.textContent for s in res.query_selector_all("span")] == ["10", "10"]

            refs["count"].value = 7
            assert [s.textContent for s in res.query_selector_all("span")] == ["14", "14"]
        finally:
            res.close()

    def test_text_element_survives_switch_patch_detach_from_node(self) -> None:
        refs: dict[str, Any] = {}

        @define_component()
        def PatchedText(context: ComponentContext[None]):
            show = use_state(lambda: True)
            base = use_state(lambda: "alpha")
            upper = use_computed(lambda: base.value.upper())
            refs["show"] = show
            refs["base"] = base
            refs["upper"] = upper
            return render_template(
                "<div>{% if show %}<span>{{ upper }}</span>{% else %}<span>static</span>{% endif %}</div>",
                {"show": show, "upper": upper},
            )

        res = TestRenderer.render(PatchedText)
        try:
            assert res.query_selector("span").textContent == "ALPHA"

            refs["show"].value = False
            assert res.query_selector("span").textContent == "static"
            assert refs["upper"].producers is not None

            refs["base"].value = "beta"
            assert refs["upper"].value == "BETA"

            refs["show"].value = True
            assert res.query_selector("span").textContent == "BETA"

            refs["base"].value = "gamma"
            assert res.query_selector("span").textContent == "GAMMA"
        finally:
            res.close()

    def test_raw_html_element_caller_computed_survives_unmount_and_patch(self) -> None:
        refs: dict[str, Any] = {}

        @define_component()
        def ConditionalRaw(context: ComponentContext[None]):
            show = use_state(lambda: True)
            label = use_state(lambda: "one")
            markup = use_computed(lambda: f"<b>{label.value}</b>")
            refs["show"] = show
            refs["label"] = label
            refs["markup"] = markup
            return html.DIV(
                {},
                SwitchElement(
                    [(show, lambda: raw_html(markup, wrapper="span"))],
                    lambda: html.P({}, "none"),
                ),
            )

        res = TestRenderer.render(ConditionalRaw)
        try:
            assert res.query_selector("span") is not None
            assert res.query_selector("span").innerHTML == "<b>one</b>"

            refs["show"].value = False
            assert refs["markup"].producers is not None

            refs["label"].value = "two"
            assert refs["markup"].value == "<b>two</b>"

            refs["show"].value = True
            assert res.query_selector("span").innerHTML == "<b>two</b>"
        finally:
            res.close()


class TestSwitchElementCallerSignalPreservation:
    def test_switch_preserves_caller_computed_cond_and_case_list_on_unmount(self) -> None:
        src = Signal(1)
        cond = Computed(lambda: src.value > 0)
        cases = Computed(lambda: [(src.value > 0, lambda: TextElement("pos"))])
        outer_show = Signal(True)
        refs: dict[str, Any] = {"outer": outer_show, "src": src, "cond": cond, "cases": cases}

        @define_component()
        def NestedSwitches(context: ComponentContext[None]):
            return html.DIV(
                {},
                SwitchElement(
                    [
                        (
                            outer_show,
                            lambda: FragmentElement(
                                [
                                    SwitchElement([(cond, lambda: html.SPAN({}, "branch-cond"))], None),
                                    SwitchElement(cases, None),
                                ]
                            ),
                        )
                    ],
                    lambda: html.P({}, "off"),
                ),
            )

        res = TestRenderer.render(NestedSwitches)
        try:
            assert res.query_selector("span") is not None
            outer_show.value = False
            assert refs["cond"].producers is not None
            assert refs["cases"].producers is not None

            src.value = -1
            assert refs["cond"].value is False
            assert refs["cases"].value[0][0] is False
        finally:
            res.close()


class TestRouterSignalOwnership:
    def test_router_link_preserves_caller_signals_across_refresh_and_unmount_and_cleans_internals(
        self, fake_browser_full
    ) -> None:
        page = RouterPage(path="/home", component=lambda _ctx: html.DIV({}, "home"))
        next_page = RouterPage(path="/next", component=lambda _ctx: html.DIV({}, "next"))
        router = Router(page, next_page, history=MockHistoryPort(mode="history"))

        to_sig = Signal("/home")
        label_src = Signal("Home")
        label_computed = Computed(lambda: f"Go {label_src.value}")
        query_sig = Signal({"tab": "all"})
        params_sig = Signal({"from": "nav"})
        path_params_sig = Signal({"id": "1"})
        active_cls_sig = Signal("is-active")

        with DIScope({_ROUTER_KEY: router}, parent=_active_di_scope.get(None)) as scope:
            parent = _make_mounted_parent()
            link = RouterLink(
                to=to_sig,
                text=[label_computed],
                query=query_sig,
                params=params_sig,
                path_params=path_params_sig,
                active_class=active_cls_sig,
            )
            link._parent = parent
            link._node_idx = 0
            asyncio.run(link._render())

            assert _active_consumer_count(router.current_match) >= 1
            assert _active_consumer_count(label_src) == 1

            to_sig.value = "/next"
            assert label_computed.producers is not None
            label_src.value = "Next"
            assert label_computed.value == "Go Next"
            assert link._get_node().textContent == "Go Next"

            link._remove_element()

            assert label_computed.producers is not None
            label_src.value = "After"
            assert label_computed.value == "Go After"
            assert link._href.producers is None
            assert link._class_attr is not None and link._class_attr.producers is None
            assert link._aria_current_attr is not None and link._aria_current_attr.producers is None
            assert _active_consumer_count(to_sig) == 0
            assert _active_consumer_count(query_sig) == 0
            assert _active_consumer_count(path_params_sig) == 0
            assert _active_consumer_count(active_cls_sig) == 0
            assert _active_consumer_count(router.current_match) == 0
            scope.dispose()

    def test_router_view_detaches_internal_level_match_on_unmount(self, fake_browser_full) -> None:
        page = RouterPage(path="/", component=lambda _ctx: html.DIV({}, "root"))
        router = Router(page, history=MockHistoryPort(mode="history"))

        with DIScope({_ROUTER_KEY: router}, parent=_active_di_scope.get(None)) as scope:
            parent = _make_mounted_parent()
            view = RouterView()
            view._parent = parent
            view._node_idx = 0
            asyncio.run(view._render())

            assert _active_consumer_count(router.current_match) >= 1
            view._remove_element()
            assert view._level_match.producers is None
            assert _active_consumer_count(router.current_match) == 0
            scope.dispose()


class TestMarkdownForSignalOwnership:
    def test_preserves_caller_iterable_on_unmount(self) -> None:
        with _markdown_scope():
            src = ReactiveList(["a", "b"])
            computed_items = Computed(lambda: [s.upper() for s in src.value])
            parent = _make_mounted_parent()
            mfe = MarkdownForElement(["item"], "items", "- {{ item }}", {"items": computed_items})
            parent._append_child(mfe)
            asyncio.run(mfe._render())

            assert _active_consumer_count(src) == 1
            assert _active_consumer_count(computed_items) == 1

            mfe._remove_element()
            assert computed_items.producers is not None
            assert _active_consumer_count(computed_items) == 0
            src.append("c")
            assert computed_items.value == ["A", "B", "C"]

    def test_reparenting_expression_iterable_avoids_duplicate_and_cleans_up(self) -> None:
        with _markdown_scope():
            items = ReactiveList(["a", "b", "c"])
            parent1 = _make_mounted_parent()
            mfe = MarkdownForElement(["item"], "items[:2]", "- {{ item }}", {"items": items})
            parent1._append_child(mfe)
            first_iterable = mfe._iterable
            assert isinstance(first_iterable, _OwnedComputed)
            assert _active_consumer_count(items) == 1

            parent2 = _make_mounted_parent()
            frag = FragmentElement([mfe])
            parent2._append_child(frag)
            assert mfe._iterable is first_iterable
            assert _active_consumer_count(items) == 1

            asyncio.run(frag._render())
            frag._remove_element()
            assert first_iterable.producers is None
            assert _active_consumer_count(items) == 0

    def test_render_markdown_for_loop_detaches_on_unmount(self) -> None:
        with _markdown_scope():
            items = ReactiveList(["x", "y"])
            doc = render_markdown("{% for item in items[:1] %}\n- {{ item }}\n{% endfor %}", {"items": items})
            parent = _make_mounted_parent()
            parent._append_child(doc)
            assert _active_consumer_count(items) == 1
            doc._remove_element()
            assert _active_consumer_count(items) == 0


class TestComponentTagOwnedPropsIsolation:
    def test_owned_prop_survives_inner_conditional_unmount_and_cleans_on_child_unmount(self) -> None:
        state_holder: dict[str, Any] = {}

        @define_component()
        def ChildBox(context: ComponentContext[dict[str, Any]]):
            visible = use_state(lambda: True)
            state_holder["visible"] = visible
            state_holder["child_props"] = context.props
            return render_template(
                "<section>{% if visible %}"
                "<span class='title'>{{ title }}</span>"
                "<ul>{% for x in items %}<li>{{ x }}</li>{% endfor %}</ul>"
                "{% endif %}</section>",
                {"visible": visible, "title": context.props["title"], "items": context.props["items"]},
            )

        @define_component()
        def ParentHost(context: ComponentContext[None]):
            mount_child = use_state(lambda: True)
            name = use_state(lambda: "Alice")
            box = use_state(lambda: {"items": ["a", "b"]})
            state_holder["mount_child"] = mount_child
            state_holder["name"] = name
            state_holder["box"] = box
            return render_template(
                "<div>{% if mount_child %}<child-box title='Hi {{ name }}' :items='box.items' />{% endif %}</div>",
                {"mount_child": mount_child, "name": name, "box": box},
            )

        res = TestRenderer.render(ParentHost)
        try:
            assert res.query_selector("span.title") is None
            assert res.query_selector("span").textContent == "Hi Alice"
            assert [li.textContent for li in res.query_selector_all("li")] == ["a", "b"]

            state_holder["visible"].value = False
            assert res.query_selector("span") is None
            assert _active_consumer_count(state_holder["name"]) == 1
            assert _active_consumer_count(state_holder["box"]) == 1

            state_holder["name"].value = "Bob"
            state_holder["box"].value = {"items": ["c"]}
            assert state_holder["child_props"]["title"].value == "Hi Bob"
            assert state_holder["child_props"]["items"].value == ["c"]

            state_holder["visible"].value = True
            assert res.query_selector("span").textContent == "Hi Bob"
            assert [li.textContent for li in res.query_selector_all("li")] == ["c"]

            state_holder["mount_child"].value = False
            assert _active_consumer_count(state_holder["name"]) == 0
            assert _active_consumer_count(state_holder["box"]) == 0
        finally:
            res.close()


class TestFrameworkOwnedComputedCleanup:
    def test_app_document_root_path_transfers_and_destroys_owned_attr_computed(self, fake_browser_full) -> None:
        cls_sig = Signal("primary")

        def root_def(_ctx: Any) -> Element:
            return render_template('<div class="theme-{{ cls }}"><span>ok</span></div>', {"cls": cls_sig})

        root_def.__webcompy_component_definition__ = True  # type: ignore[attr-defined]
        with DIScope({_HEAD_PROPS_KEY: HeadPropsStore()}, parent=_active_di_scope.get(None)) as scope:
            parent = _make_mounted_parent()
            comp = Component(root_def, None, {}, generator=None)
            assert _active_consumer_count(cls_sig) == 1
            assert "__attr_class" in comp.__signal_members__

            comp._parent = parent
            comp._node_idx = 0
            asyncio.run(comp._render())
            comp._remove_element()
            assert _active_consumer_count(cls_sig) == 0
            scope.dispose()

    def test_template_expressions_multiline_dict_row_and_radio_bind_clean_up_on_unmount(self) -> None:
        refs: dict[str, Any] = {}

        @define_component()
        def OwnedHarness(context: ComponentContext[None]):
            show = use_state(lambda: True)
            count = use_state(lambda: 2)
            items = use_reactive_list(lambda: ["a", "b", "c"])
            mapping = use_reactive_dict(lambda: {"k1": "v1"})
            multi = use_state(lambda: "line1\nline2")
            choice = use_state(lambda: "a")
            refs["show"] = show
            refs["count"] = count
            refs["items"] = items
            refs["mapping"] = mapping
            refs["multi"] = multi
            refs["choice"] = choice

            tmpl = render_template(
                "<div>{% if show %}"
                "<div class='c-{{ count }}'>{{ count + 1 }}"
                "<ul>{% for item in items[:2] %}<li>{{ item }}</li>{% endfor %}</ul>"
                "<dl>{% for k, v in mapping %}<dd>{{ k }}:{{ v }}</dd>{% endfor %}</dl>"
                "</div>"
                "{% endif %}</div>",
                {"show": show, "count": count, "items": items, "mapping": mapping},
            )
            multi_el = MultiLineTextElement(multi)
            radio_el = html.INPUT({"type": "radio", "value": "a", ":bind": choice})
            switch_extra = SwitchElement([(show, lambda: FragmentElement([multi_el, radio_el]))], None)
            tmpl._append_child(switch_extra)
            return tmpl

        res = TestRenderer.render(OwnedHarness)
        try:
            assert _active_consumer_count(refs["count"]) >= 2
            assert _active_consumer_count(refs["items"]) >= 1
            assert _active_consumer_count(refs["mapping"]) >= 1
            assert _active_consumer_count(refs["multi"]) >= 1
            assert _active_consumer_count(refs["choice"]) >= 1

            refs["show"].value = False
            assert _active_consumer_count(refs["count"]) == 0
            assert _active_consumer_count(refs["items"]) == 0
            assert _active_consumer_count(refs["mapping"]) == 0
            assert _active_consumer_count(refs["multi"]) == 0
            assert _active_consumer_count(refs["choice"]) == 0
        finally:
            res.close()

    def test_observed_props_excluded_from_signal_members_and_transfer_collection(self) -> None:
        @define_component(custom_element_name="x-owned-observed-test", observed_attributes=("label",))
        def ObservedWidget(context: ComponentContext[dict[str, Any]]):
            return html.SPAN({}, str(context.props.get("label") or ""))

        res = TestRenderer.render(ObservedWidget)
        try:
            instance = res._instance
            assert isinstance(instance, Component)
            assert "_observed_props" not in getattr(instance, "__signal_members__", {})
            assert "_observed_props" not in _collect_component_signals(instance)
        finally:
            res.close()

    def test_direct_signal_receivable_subclass_still_auto_tracks_attributes(self) -> None:
        src = Signal(3)

        class DirectReceiver(SignalReceivable):
            def __init__(self) -> None:
                self.direct = Signal(1)
                self.derived = Computed(lambda: src.value * 2)

        receiver = DirectReceiver()
        assert set(receiver.__signal_members__.keys()) == {"direct", "derived"}
        assert _active_consumer_count(src) == 1
        receiver.__purge_signal_members__()
        assert receiver.__signal_members__ == {}
        assert _active_consumer_count(src) == 0


class TestRawHtmlDirectElement:
    def test_raw_html_preserves_caller_computed_on_detach_and_remove(self, fake_browser_full) -> None:
        src = Signal("hi")
        derived = Computed(lambda: f"<em>{src.value}</em>")
        el = RawHTMLElement(derived)
        parent = _make_mounted_parent()
        el._parent = parent
        el._node_idx = 0
        asyncio.run(el._render())
        el._detach_from_node()
        el._remove_element()
        assert derived.producers is not None
        src.value = "bye"
        assert derived.value == "<em>bye</em>"
