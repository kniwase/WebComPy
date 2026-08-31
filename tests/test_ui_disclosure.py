"""Unit tests for disclosure and feedback components (browserless via TestRenderer)."""

from __future__ import annotations

from typing import Any

from webcompy.components import define_component
from webcompy.elements import html
from webcompy.signal import use_state
from webcompy_server.ports._virtual_dom import VirtualDOMEvent
from webcompy_testing import TestRenderer


def _find_all(node: Any, predicate: Any) -> list:
    """Collect virtual descendants of ``node`` matching ``predicate``."""
    from webcompy_server.ports import VirtualDOMNode

    found: list = []
    stack = [node]
    while stack:
        current = stack.pop()
        if predicate(current):
            found.append(current)
        for i in range(current.childNodes.length - 1, -1, -1):
            child = current.childNodes[i]
            if isinstance(child, VirtualDOMNode):
                stack.append(child)
    return found


def _by_role(root: Any, role: str) -> list:
    return _find_all(root, lambda n: n.getAttribute("role") == role)


def _by_class(root: Any, cls: str) -> list:
    return _find_all(root, lambda n: cls in (n.getAttribute("class") or ""))


def _click(node: Any) -> None:
    node.dispatchEvent(VirtualDOMEvent("click", bubbles=True, cancelable=True))


def _keydown(node: Any, key: str) -> None:
    event = VirtualDOMEvent("keydown", bubbles=True, cancelable=True)
    event.key = key  # type: ignore[attr-defined]
    node.dispatchEvent(event)


def _make_tabs() -> list:
    return [
        {"key": "a", "label": "Tab A", "content": lambda: html.INPUT({"data-testid": "input-a"})},
        {"key": "b", "label": "Tab B", "content": lambda: html.SPAN({"data-testid": "panel-b"}, "B")},
    ]


class _FakeAppCtx:
    """Minimal app context providing deterministic per-instance transfer ids."""

    def __init__(self) -> None:
        from webcompy.components._libs import generate_id

        self._generate_id = generate_id
        self._counters: dict[str, int] = {}
        self._defer_depth = 0
        self._deferred_callbacks: list = []
        self._hydration_payload_closed = False
        self._config = type("Config", (), {"on_error": staticmethod(lambda exc: None)})()

    def _next_transfer_id(self, name: str) -> str:
        ordinal = self._counters.get(name, 0)
        self._counters[name] = ordinal + 1
        return f"{self._generate_id(name)}#{ordinal}"


class TestTabs:
    """Tabs: ARIA wiring, persistence, keyboard model, ids, control modes."""

    def test_aria_wiring(self) -> None:
        @define_component(custom_element_name="test-tabs-wiring")
        def Page(ctx):
            from webcompy.ui import Tabs

            return Tabs({"tabs": _make_tabs()})

        with TestRenderer.render(Page) as result:
            root = result.body_node
            tab_btns = _by_role(root, "tab")
            panels = _by_role(root, "tabpanel")
            assert len(tab_btns) == 2 and len(panels) == 2
            assert tab_btns[0].getAttribute("aria-selected") == "true"
            assert tab_btns[1].getAttribute("aria-selected") == "false"
            assert tab_btns[0].getAttribute("data-state") == "active"
            assert tab_btns[1].getAttribute("data-state") == "inactive"
            assert panels[0].getAttribute("data-state") == "active"
            assert panels[1].getAttribute("data-state") == "inactive"
            assert tab_btns[0].getAttribute("aria-controls") == panels[0].getAttribute("id")
            assert panels[0].getAttribute("aria-labelledby") == tab_btns[0].getAttribute("id")
            assert tab_btns[0].getAttribute("tabindex") == "0"
            assert tab_btns[1].getAttribute("tabindex") == "-1"

    def test_panel_state_preservation(self) -> None:
        captured: dict = {}

        @define_component(custom_element_name="test-tabs-persist")
        def Page(ctx):
            from webcompy.ui import Tabs

            sig = use_state(lambda: "a")
            captured["sig"] = sig
            return Tabs({"tabs": _make_tabs(), "active": sig})

        with TestRenderer.render(Page) as result:
            root = result.body_node
            input_a = _find_all(root, lambda n: n.getAttribute("data-testid") == "input-a")[0]
            panels = _by_role(root, "tabpanel")
            captured["sig"].value = "b"
            assert panels[0].getAttribute("hidden") == ""
            assert panels[1].getAttribute("hidden") is None
            captured["sig"].value = "a"
            assert panels[0].getAttribute("hidden") is None
            # The same input node survived both switches (no remount): panel
            # state (e.g. typed text) persists while hidden.
            assert _find_all(root, lambda n: n is input_a)

    def test_uncontrolled_click_activation(self) -> None:
        selected: list = []

        @define_component(custom_element_name="test-tabs-click")
        def Page(ctx):
            from webcompy.ui import Tabs

            return Tabs({"tabs": _make_tabs(), "on_select": lambda key: selected.append(key)})

        with TestRenderer.render(Page) as result:
            root = result.body_node
            tab_btns = _by_role(root, "tab")
            _click(tab_btns[1])
            assert selected == ["b"]
            assert tab_btns[1].getAttribute("aria-selected") == "true"
            assert tab_btns[0].getAttribute("aria-selected") == "false"

    def test_parent_controlled_click_only_calls_back(self) -> None:
        selected: list = []

        @define_component(custom_element_name="test-tabs-controlled")
        def Page(ctx):
            from webcompy.ui import Tabs

            return Tabs({"tabs": _make_tabs(), "active": "a", "on_select": lambda key: selected.append(key)})

        with TestRenderer.render(Page) as result:
            root = result.body_node
            tab_btns = _by_role(root, "tab")
            _click(tab_btns[1])
            assert selected == ["b"]
            # Parent did not update the prop: selection stays on tab A.
            assert tab_btns[0].getAttribute("aria-selected") == "true"
            assert tab_btns[1].getAttribute("aria-selected") == "false"

    def test_keyboard_navigation_wraps_and_activates(self) -> None:
        @define_component(custom_element_name="test-tabs-keys")
        def Page(ctx):
            from webcompy.ui import Tabs

            return Tabs(
                {
                    "tabs": [
                        {"key": "k0", "label": "L0", "content": lambda: html.SPAN({}, "P0")},
                        {"key": "k1", "label": "L1", "content": lambda: html.SPAN({}, "P1")},
                        {"key": "k2", "label": "L2", "content": lambda: html.SPAN({}, "P2")},
                    ]
                }
            )

        with TestRenderer.render(Page) as result:
            root = result.body_node
            tab_btns = _by_role(root, "tab")
            tablist = _by_role(root, "tablist")[0]
            _keydown(tablist, "ArrowRight")
            assert tab_btns[1].getAttribute("aria-selected") == "true"
            _keydown(tablist, "ArrowRight")
            _keydown(tablist, "ArrowRight")
            assert tab_btns[0].getAttribute("aria-selected") == "true"  # wrapped
            _keydown(tablist, "End")
            assert tab_btns[2].getAttribute("aria-selected") == "true"
            _keydown(tablist, "Home")
            assert tab_btns[0].getAttribute("aria-selected") == "true"
            _keydown(tablist, "ArrowLeft")
            assert tab_btns[2].getAttribute("aria-selected") == "true"  # wraps backward

    def test_keyboard_moves_focus(self) -> None:
        @define_component(custom_element_name="test-tabs-focus")
        def Page(ctx):
            from webcompy.ui import Tabs

            return Tabs({"tabs": _make_tabs()})

        with TestRenderer.render(Page) as result:
            from webcompy.ports._keys import HOST_PORT_KEY

            root = result.body_node
            tab_btns = _by_role(root, "tab")
            tablist = _by_role(root, "tablist")[0]
            host_port = result._scope.inject(HOST_PORT_KEY, default=None)

            def active():
                if host_port is None:
                    return None
                getter = host_port.create_js_global_getter(
                    "document",
                    wrapper=lambda doc: getattr(doc, "activeElement", None) if doc is not None else None,
                )
                return getter()

            _click(tab_btns[0])  # noop activation; just ensure no error
            _keydown(tablist, "ArrowRight")
            assert active() is tab_btns[1]

    def test_two_tabs_distinct_hydration_stable_ids(self) -> None:
        from webcompy.components._component import _active_app_context

        app_ctx = _FakeAppCtx()

        @define_component(custom_element_name="test-tabs-dup-ids")
        def Page(ctx):
            from webcompy.ui import Tabs

            tabs = _make_tabs()
            return html.DIV({}, Tabs({"tabs": tabs, "aria_label": "One"}), Tabs({"tabs": tabs, "aria_label": "Two"}))

        token = _active_app_context.set(app_ctx)
        try:
            with TestRenderer.render(Page) as result:
                root = result.body_node
                panels = _by_role(root, "tabpanel")
                assert len(panels) == 4
                panel_ids = {p.getAttribute("id") for p in panels}
                assert len(panel_ids) == 4  # unique across instances
                # Each tab references its own panel: check pairing stability per group.
                tab_btns = _by_role(root, "tab")
                for i, tab in enumerate(tab_btns):
                    expected = panels[i].getAttribute("id")
                    assert tab.getAttribute("aria-controls") == expected
                    assert panels[i].getAttribute("aria-labelledby") == tab.getAttribute("id")
        finally:
            _active_app_context.reset(token)


class TestCollapse:
    """Collapse: trigger ARIA across toggle, data-state, animation paths."""

    def test_uncontrolled_toggle(self) -> None:
        @define_component(custom_element_name="test-collapse-toggle")
        def Page(ctx):
            from webcompy.ui import Collapse

            return Collapse(
                {"transition_name": None}, slots={"trigger": lambda: "T", "default": lambda: html.P({}, "BODY")}
            )

        with TestRenderer.render(Page) as result:
            root = result.body_node
            trigger = _find_all(root, lambda n: n.getAttribute("aria-expanded") is not None)[0]
            assert trigger.getAttribute("aria-expanded") == "false"
            assert trigger.getAttribute("data-state") == "closed"
            assert trigger.getAttribute("aria-controls") == trigger.getAttribute("aria-controls")
            _click(trigger)
            contents = _by_role(root, "region")
            assert len(contents) == 1
            assert contents[0].getAttribute("data-state") == "open"
            assert contents[0].getAttribute("id") == trigger.getAttribute("aria-controls")
            assert trigger.getAttribute("aria-expanded") == "true"
            assert trigger.getAttribute("data-state") == "open"
            _click(trigger)
            result.transition_port.flush_frame()
            assert _by_role(root, "region") == []
            assert trigger.getAttribute("data-state") == "closed"

    def test_signal_control_writes_through(self) -> None:
        captured: dict = {}

        @define_component(custom_element_name="test-collapse-signal")
        def Page(ctx):
            from webcompy.ui import Collapse

            sig = use_state(lambda: False)
            captured["sig"] = sig
            return Collapse({"open": sig, "transition_name": None}, slots={"default": lambda: html.P({}, "X")})

        with TestRenderer.render(Page) as result:
            root = result.body_node
            trigger = _find_all(root, lambda n: n.getAttribute("aria-expanded") is not None)[0]
            _click(trigger)
            assert captured["sig"].value is True

    def test_plain_boolean_delegates_to_callback(self) -> None:
        changes: list = []

        @define_component(custom_element_name="test-collapse-plain")
        def Page(ctx):
            from webcompy.ui import Collapse

            return Collapse(
                {"open": False, "on_toggle": lambda v: changes.append(v), "transition_name": None},
                slots={"default": lambda: html.P({}, "X")},
            )

        with TestRenderer.render(Page) as result:
            root = result.body_node
            trigger = _find_all(root, lambda n: n.getAttribute("aria-expanded") is not None)[0]
            _click(trigger)
            assert changes == [True]
            assert _by_role(root, "region") == []  # parent owns state; nothing mounted


class TestAccordion:
    """Accordion: key-based identity and open policy."""

    def _items(self) -> list:
        return [
            {"key": "i1", "label": "One", "content": lambda: html.P({}, "C1")},
            {"key": "i2", "label": "Two", "content": lambda: html.P({}, "C2")},
        ]

    def test_single_open_policy_closes_siblings(self) -> None:
        @define_component(custom_element_name="test-accordion-single")
        def Page(ctx):
            from webcompy.ui import Accordion

            return Accordion({"items": self._items(), "single_open": True})

        with TestRenderer.render(Page) as result:
            root = result.body_node
            triggers = _find_all(root, lambda n: n.getAttribute("aria-expanded") is not None)
            assert len(triggers) == 2
            _click(triggers[0])
            assert len(_by_role(root, "region")) == 1
            _click(triggers[1])
            result.transition_port.flush_frame()
            regions = _by_role(root, "region")
            assert len(regions) == 1
            assert regions[0].getAttribute("aria-labelledby") == triggers[1].getAttribute("id")
            assert triggers[0].getAttribute("data-state") == "closed"
            assert triggers[1].getAttribute("data-state") == "open"

    def test_multi_open_default(self) -> None:
        @define_component(custom_element_name="test-accordion-multi")
        def Page(ctx):
            from webcompy.ui import Accordion

            return Accordion({"items": self._items()})

        with TestRenderer.render(Page) as result:
            root = result.body_node
            triggers = _find_all(root, lambda n: n.getAttribute("aria-expanded") is not None)
            _click(triggers[0])
            _click(triggers[1])
            assert len(_by_role(root, "region")) == 2


class TestAlert:
    """Alert: variant role mapping and dismiss behavior."""

    def test_variant_role_mapping(self) -> None:
        variants = ["info", "success", "warning", "error", "bogus"]
        expected_roles = ["status", "status", "alert", "alert", "status"]

        @define_component(custom_element_name="test-alert-variants")
        def Page(ctx):
            from webcompy.ui import Alert

            return html.DIV({}, *[Alert({"variant": v}, slots={"default": lambda vv=v: f"m-{vv}"}) for v in variants])

        with TestRenderer.render(Page) as result:
            root = result.body_node
            alerts = _find_all(root, lambda n: n.getAttribute("data-variant") is not None)
            assert len(alerts) == len(variants)
            roles = [a.getAttribute("role") for a in alerts]
            assert roles == expected_roles
            # Unknown variants normalize to info on both attributes.
            assert alerts[-1].getAttribute("data-variant") == "info"

    def test_dismiss_hides_and_calls_back(self) -> None:
        dismissed: list = []

        @define_component(custom_element_name="test-alert-dismiss")
        def Page(ctx):
            from webcompy.ui import Alert

            return Alert(
                {"variant": "error", "dismissable": True, "on_dismiss": lambda: dismissed.append(1)},
                slots={"default": lambda: "Boom"},
            )

        with TestRenderer.render(Page) as result:
            root = result.body_node
            alert = _find_all(root, lambda n: n.getAttribute("role") == "alert")[0]
            button = _by_role(root, "button") or _find_all(root, lambda n: n.getAttribute("aria-label") == "Dismiss")
            assert len(button) == 1
            assert alert.getAttribute("hidden") is None
            _click(button[0])
            assert dismissed == [1]
            assert alert.getAttribute("hidden") == ""


class TestProgress:
    """Progress: determinate/indeterminate ARIA and reactive value."""

    def test_determinate_aria(self) -> None:
        @define_component(custom_element_name="test-progress-det")
        def Page(ctx):
            from webcompy.ui import Progress

            return Progress({"value": 40, "aria_label": "Upload"})

        with TestRenderer.render(Page) as result:
            root = result.body_node
            bar = _by_role(root, "progressbar")[0]
            assert bar.getAttribute("aria-valuenow") == "40"
            assert bar.getAttribute("aria-valuemin") == "0"
            assert bar.getAttribute("aria-valuemax") == "100"
            assert bar.getAttribute("data-state") == "determinate"
            assert bar.getAttribute("aria-label") == "Upload"
            fill = _by_class(root, "webcompy-progress-fill")[0]
            assert "width: 40.0000%" in (fill.getAttribute("style") or "")

    def test_indeterminate_omits_valuenow(self) -> None:
        @define_component(custom_element_name="test-progress-ind")
        def Page(ctx):
            from webcompy.ui import Progress

            return Progress({"indeterminate": True, "aria_label": "Loading"})

        with TestRenderer.render(Page) as result:
            root = result.body_node
            bar = _by_role(root, "progressbar")[0]
            assert bar.getAttribute("aria-valuenow") is None
            assert bar.getAttribute("data-state") == "indeterminate"
            fill = _by_class(root, "webcompy-progress-fill")[0]
            assert fill.getAttribute("style") is None

    def test_reactive_value_updates(self) -> None:
        captured: dict = {}

        @define_component(custom_element_name="test-progress-react")
        def Page(ctx):
            from webcompy.ui import Progress

            sig = use_state(lambda: 10)
            captured["sig"] = sig
            return Progress({"value": sig, "aria_label": "X"})

        with TestRenderer.render(Page) as result:
            root = result.body_node
            bar = _by_role(root, "progressbar")[0]
            assert bar.getAttribute("aria-valuenow") == "10"
            captured["sig"].value = 75
            assert bar.getAttribute("aria-valuenow") == "75"
            fill = _by_class(root, "webcompy-progress-fill")[0]
            assert "width: 75.0000%" in (fill.getAttribute("style") or "")


class TestBadgeSkeletonCard:
    """Badge variants, Skeleton decoration, Card regions, class pass-through."""

    def test_badge_variant_and_fallback(self) -> None:
        @define_component(custom_element_name="test-badge-variants")
        def Page(ctx):
            from webcompy.ui import Badge

            return html.DIV(
                {},
                Badge({"variant": "error"}, slots={"default": lambda: "E"}),
                Badge({"variant": "nope"}, slots={"default": lambda: "N"}),
            )

        with TestRenderer.render(Page) as result:
            root = result.body_node
            badges = _find_all(root, lambda n: n.getAttribute("data-variant") is not None)
            variants = {b.getAttribute("data-variant") for b in badges}
            assert variants == {"error", "neutral"}
            assert any("webcompy-badge--error" in (b.getAttribute("class") or "") for b in badges)

    def test_skeleton_decorative(self) -> None:
        @define_component(custom_element_name="test-skeleton-shapes")
        def Page(ctx):
            from webcompy.ui import Skeleton

            return html.DIV(
                {},
                Skeleton({"shape": "line"}),
                Skeleton({"shape": "circle", "width": "2rem"}),
            )

        with TestRenderer.render(Page) as result:
            root = result.body_node
            skeletons = _find_all(
                root, lambda n: n.getAttribute("aria-hidden") == "true" and n.getAttribute("data-shape")
            )
            assert len(skeletons) == 2
            shapes = {s.getAttribute("data-shape") for s in skeletons}
            assert shapes == {"line", "circle"}
            circ = next(s for s in skeletons if s.getAttribute("data-shape") == "circle")
            assert "width: 2rem" in (circ.getAttribute("style") or "")

    def test_card_regions_and_class_passthrough(self) -> None:
        @define_component(custom_element_name="test-card-regions")
        def Page(ctx):
            from webcompy.ui import Card

            return html.DIV(
                {},
                Card(
                    {"class_name": "mine"},
                    slots={
                        "header": lambda: "H",
                        "default": lambda: "B",
                        "footer": lambda: "F",
                    },
                ),
                Card({}, slots={"default": lambda: "B2"}),
            )

        with TestRenderer.render(Page) as result:
            root = result.body_node
            assert len(_by_class(root, "webcompy-card-header")) == 1
            assert len(_by_class(root, "webcompy-card-body")) == 2
            assert len(_by_class(root, "webcompy-card-footer")) == 1
            card_roots = _by_class(root, "webcompy-card")
            full = card_roots[0] if "mine" in (card_roots[0].getAttribute("class") or "") else card_roots[1]
            cls = (full.getAttribute("class") or "").split()
            assert cls[-1] == "mine"  # user class appended last
            assert "webcompy-card" in cls


class TestPairContracts:
    """Headless/themed pairs resolve through the three import paths."""

    def test_import_paths_and_headless_markers(self) -> None:
        import webcompy.ui as ui
        from webcompy.ui import headless as headless_ns
        from webcompy.ui.components import Tabs as ThemedTabs
        from webcompy.ui.headless import Tabs as HeadlessTabs

        assert ui.Tabs is ThemedTabs
        assert headless_ns.Tabs is HeadlessTabs
        for name in ("Tabs", "Collapse", "Accordion", "Alert", "Progress", "Badge", "Skeleton", "Card"):
            assert hasattr(headless_ns, name)
            assert hasattr(ui, name)

    def test_primitives_stylesheet_ships_disclosure_rules(self) -> None:
        from webcompy.ui._styles import get_styles_file

        css = get_styles_file("primitives.css").decode("utf-8")
        for marker in (
            ".webcompy-tabs-tablist",
            ".webcompy-tabs-tab",
            ".webcompy-collapse-content",
            ".webcompy-collapse-enter-active",
            ".webcompy-collapse-leave-to",
            ".webcompy-alert--error",
            ".webcompy-progress-fill",
            ".webcompy-badge--success",
            ".webcompy-skeleton",
            ".webcompy-card-footer",
        ):
            assert marker in css, marker
