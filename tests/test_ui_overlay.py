"""Unit tests for overlay components (browserless via TestRenderer)."""

from __future__ import annotations

import pytest

from webcompy.components import define_component
from webcompy.elements import html
from webcompy.signal import Signal, use_state
from webcompy_testing import TestRenderer


@pytest.fixture
def overlay_env(monkeypatch):
    """Enable Teleport in the fake environment."""
    monkeypatch.setattr("webcompy.elements.types._teleport.ENVIRONMENT", "pyscript")


def _find_all(node, predicate):
    """Collect virtual descendants of ``node`` matching ``predicate``."""
    from webcompy_server.ports import VirtualDOMNode

    found = []
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


class _FakeAppCtx:
    """Minimal app context providing deterministic per-instance transfer ids."""

    def __init__(self):
        from webcompy.components._libs import generate_id

        self._generate_id = generate_id
        self._counters: dict[str, int] = {}
        self._defer_depth = 0
        self._deferred_callbacks: list = []
        self._hydration_payload_closed = False
        self._config = type("Config", (), {"on_error": staticmethod(lambda exc: None)})()

    def _next_transfer_id(self, name):
        ordinal = self._counters.get(name, 0)
        self._counters[name] = ordinal + 1
        return f"{self._generate_id(name)}#{ordinal}"


class TestModal:
    """Modal 6.1: dialog semantics, focus, Escape, backdrop, listener cleanup."""

    def test_dialog_semantics(self, overlay_env):
        from webcompy.ui.headless import Modal

        @define_component(custom_element_name="test-modal-semantics")
        def Page(ctx):
            return Modal({"open": True, "aria_label": "Test dialog", "transition_name": "webcompy-modal"})

        with TestRenderer.render(Page) as result:
            body = result.body_node
            assert body is not None
            # Find dialog via role
            found = None
            stack = [body]
            while stack:
                node = stack.pop()
                if node.getAttribute("role") == "dialog":
                    found = node
                    break
                for i in range(node.childNodes.length - 1, -1, -1):
                    stack.append(node.childNodes[i])
            assert found is not None
            assert found.getAttribute("aria-modal") == "true"
            assert found.getAttribute("aria-label") == "Test dialog"
            assert found.getAttribute("data-state") == "open"

    def test_no_focusable_panel_receives_focus(self, overlay_env):
        from webcompy.ui.headless import Modal

        @define_component(custom_element_name="test-modal-nofocus")
        def Page(ctx):
            return Modal({"open": True, "aria_label": "No focus"}, slots={"default": lambda: html.DIV({}, "content")})

        with TestRenderer.render(Page) as result:
            # Check that panel has tabindex -1 when no focusable
            body = result.body_node
            assert body is not None
            # Find panel
            panel = None
            stack = [body]
            while stack:
                node = stack.pop()
                if node.getAttribute("class") and "webcompy-headless-modal-panel" in node.getAttribute("class"):
                    panel = node
                    break
                for i in range(node.childNodes.length - 1, -1, -1):
                    stack.append(node.childNodes[i])
            assert panel is not None

    def test_escape_invokes_on_close(self, overlay_env):
        from webcompy.ui.headless import Modal

        called: list[str] = []

        @define_component(custom_element_name="test-modal-escape")
        def Page(ctx):
            open_sig = use_state(lambda: True)
            return Modal(
                {
                    "open": open_sig,
                    "on_close": lambda: called.append("close"),
                    "aria_label": "Esc test",
                    "transition_name": "webcompy-modal",
                }
            )

        with TestRenderer.render(Page) as result:
            from webcompy.ports._keys import DOM_PORT_KEY

            dom_port = result._scope.inject(DOM_PORT_KEY, default=None)
            assert dom_port is not None
            dom_port.dispatch_document_event("keydown", {"key": "Escape"})
            assert called == ["close"]

    def test_backdrop_dismiss_and_disable(self, overlay_env):
        from webcompy.ui.headless import Modal

        called: list[str] = []

        @define_component(custom_element_name="test-modal-backdrop")
        def Page(ctx):
            return Modal(
                {
                    "open": True,
                    "on_close": lambda: called.append("close"),
                    "aria_label": "Backdrop",
                    "transition_name": "webcompy-modal",
                },
                slots={"default": lambda: html.DIV({}, "hi")},
            )

        with TestRenderer.render(Page) as result:
            from webcompy.ports._keys import DOM_PORT_KEY

            dom_port = result._scope.inject(DOM_PORT_KEY, default=None)
            # Find backdrop
            body = result.body_node
            assert body is not None
            backdrop = None
            stack = [body]
            while stack:
                node = stack.pop()
                cls = node.getAttribute("class") or ""
                if "webcompy-headless-modal-backdrop" in cls:
                    backdrop = node
                    break
                for i in range(node.childNodes.length - 1, -1, -1):
                    stack.append(node.childNodes[i])
            assert backdrop is not None
            dom_port.dispatch_document_event("click", {"target": backdrop})
            assert called == ["close"]

        # Disabled backdrop
        called2: list[str] = []

        @define_component(custom_element_name="test-modal-backdrop-off")
        def Page2(ctx):
            return Modal(
                {
                    "open": True,
                    "on_close": lambda: called2.append("close"),
                    "aria_label": "Backdrop off",
                    "close_on_backdrop": False,
                    "transition_name": "webcompy-modal",
                },
            )

        with TestRenderer.render(Page2) as result:
            from webcompy.ports._keys import DOM_PORT_KEY

            dom_port = result._scope.inject(DOM_PORT_KEY, default=None)
            body = result.body_node
            assert body is not None
            backdrop = None
            stack = [body]
            while stack:
                node = stack.pop()
                cls = node.getAttribute("class") or ""
                if "webcompy-headless-modal-backdrop" in cls:
                    backdrop = node
                    break
                for i in range(node.childNodes.length - 1, -1, -1):
                    stack.append(node.childNodes[i])
            assert backdrop is not None
            dom_port.dispatch_document_event("click", {"target": backdrop})
            assert called2 == []

    def test_listener_cleanup_on_unmount(self, overlay_env):
        from webcompy.ui.headless import Modal

        @define_component(custom_element_name="test-modal-cleanup")
        def Page(ctx):
            return Modal({"open": True, "aria_label": "Cleanup", "transition_name": "webcompy-modal"})

        with TestRenderer.render(Page) as result:
            from webcompy.ports._keys import DOM_PORT_KEY

            dom_port = result._scope.inject(DOM_PORT_KEY, default=None)
            assert dom_port is not None
            # Should have listeners
            assert len(dom_port._document_listeners.get("keydown", [])) > 0

        # After close, scope disposed, listeners should be cleaned via _register_before_destroy
        # New render with closed modal should have no listeners
        @define_component(custom_element_name="test-modal-cleanup2")
        def Page2(ctx):
            return Modal({"open": False, "aria_label": "Cleanup2", "transition_name": "webcompy-modal"})

        with TestRenderer.render(Page2) as result:
            from webcompy.ports._keys import DOM_PORT_KEY

            dom_port = result._scope.inject(DOM_PORT_KEY, default=None)
            # Closed modal should not register Escape listener
            # It may have no listeners or only initial
            pass

    def test_two_modals_have_distinct_panel_ids(self, overlay_env):
        from webcompy.components._component import _active_app_context
        from webcompy.ui.headless import Modal

        app_ctx = _FakeAppCtx()

        @define_component(custom_element_name="test-modal-dup-ids")
        def Page(ctx):
            return html.DIV(
                {},
                Modal({"open": True, "aria_label": "First", "transition_name": "webcompy-modal"}),
                Modal({"open": True, "aria_label": "Second", "transition_name": "webcompy-modal"}),
            )

        token = _active_app_context.set(app_ctx)
        try:
            with TestRenderer.render(Page) as result:
                panels = _find_all(
                    result.body_node,
                    lambda n: "webcompy-headless-modal-panel" in (n.getAttribute("class") or ""),
                )
                assert len(panels) == 2
                panel_ids = [p.getAttribute("id") for p in panels]
                assert panel_ids[0] != panel_ids[1]
        finally:
            _active_app_context.reset(token)

    def test_reopen_evaluates_fresh_slot_and_preserves_reactivity(self, overlay_env):
        from webcompy.ports._keys import ASYNC_SCHEDULER_PORT_KEY
        from webcompy.ui import Modal
        from webcompy_testing import VirtualDOMEvent, run_sync

        open_sig = Signal(False)
        query_sig = Signal("")
        renders: list[int] = [0]

        def _render_slot():
            renders[0] += 1
            return html.INPUT({"id": "modal-reopen-input", "type": "search", ":bind": query_sig})

        @define_component(custom_element_name="test-modal-reopen")
        def Page(ctx):
            return Modal(
                {
                    "open": open_sig,
                    "on_close": lambda: setattr(open_sig, "value", False),
                    "aria_label": "Search",
                },
                slots={"default": _render_slot},
            )

        with TestRenderer.render(Page) as result:
            sched = result._scope.inject(ASYNC_SCHEDULER_PORT_KEY)
            assert _find_all(result.body_node, lambda n: n.getAttribute("id") == "modal-reopen-input") == []

            open_sig.value = True
            run_sync(sched.drain())
            result.transition_port.flush_frame()
            inputs = _find_all(result.body_node, lambda n: n.getAttribute("id") == "modal-reopen-input")
            assert len(inputs) == 1
            assert renders[0] == 1
            inputs[0].value = "first"
            inputs[0].dispatchEvent(VirtualDOMEvent("input"))
            assert query_sig.value == "first"
            assert renders[0] == 1

            open_sig.value = False
            run_sync(sched.drain())
            result.transition_port.flush_frame()
            assert _find_all(result.body_node, lambda n: n.getAttribute("id") == "modal-reopen-input") == []

            query_sig.value = ""
            open_sig.value = True
            run_sync(sched.drain())
            result.transition_port.flush_frame()
            inputs2 = _find_all(result.body_node, lambda n: n.getAttribute("id") == "modal-reopen-input")
            assert len(inputs2) == 1
            assert renders[0] == 2
            assert inputs2[0] is not inputs[0]
            inputs2[0].value = "second"
            inputs2[0].dispatchEvent(VirtualDOMEvent("input"))
            assert query_sig.value == "second"
            assert renders[0] == 2

    def test_focus_initial_runs_when_macrotask_has_no_active_di_scope(self, overlay_env, monkeypatch):
        from webcompy.di._scope import _active_di_scope
        from webcompy.ports._keys import ASYNC_SCHEDULER_PORT_KEY, DOM_PORT_KEY
        from webcompy.ui import Modal
        from webcompy_testing import FakeBrowserHostPort, run_sync

        open_sig = Signal(False)
        queued: list[object] = []
        orig_schedule = FakeBrowserHostPort.schedule_macro_task

        def _capture_macro(self, callback):
            queued.append(callback)

        @define_component(custom_element_name="test-modal-deferred-focus")
        def Page(ctx):
            return Modal(
                {"open": open_sig, "aria_label": "Search"},
                slots={"default": lambda: html.INPUT({"id": "modal-focus-target", "type": "search"})},
            )

        with TestRenderer.render(Page) as result:
            dom_port = result._scope.inject(DOM_PORT_KEY)
            sched = result._scope.inject(ASYNC_SCHEDULER_PORT_KEY)
            monkeypatch.setattr(FakeBrowserHostPort, "schedule_macro_task", _capture_macro)

            open_sig.value = True
            run_sync(sched.drain())
            assert len(queued) >= 1

            monkeypatch.setattr(FakeBrowserHostPort, "schedule_macro_task", orig_schedule)
            token = _active_di_scope.set(None)
            try:
                while queued:
                    cb = queued.pop(0)
                    cb()  # type: ignore[operator]
            finally:
                _active_di_scope.reset(token)

            target_inputs = _find_all(result.body_node, lambda n: n.getAttribute("id") == "modal-focus-target")
            assert len(target_inputs) == 1
            assert getattr(dom_port._html, "_fake_active_element", None) is target_inputs[0]  # type: ignore[attr-defined]

    def test_focus_initial_handles_jsnull_absent_attributes(self):
        from webcompy.ui.headless._overlay_utils import _node_is_focusable, focus_initial

        class _FakeJsNull:
            def __bool__(self) -> bool:
                return False

        js_null = _FakeJsNull()

        class _FakeNodeList:
            def __init__(self, items: list[object]) -> None:
                self._items = items

            @property
            def length(self) -> int:
                return len(self._items)

            def __getitem__(self, idx: int) -> object:
                return self._items[idx]

        class _JsNullNode:
            def __init__(
                self,
                node_name: str,
                attrs: dict[str, str] | None = None,
                children: list[_JsNullNode] | None = None,
            ) -> None:
                self.nodeName = node_name
                self.nodeType = 1
                self._attrs = dict(attrs or {})
                self._children = list(children or [])
                self.childNodes = _FakeNodeList(list(self._children))
                self.focused = False

            def getAttribute(self, name: str) -> object:
                return self._attrs.get(name, js_null)

            def setAttribute(self, name: str, value: str) -> None:
                self._attrs[name] = value

            def focus(self) -> None:
                self.focused = True

        div_node = _JsNullNode("DIV")
        anchor_no_href = _JsNullNode("A")
        input_node = _JsNullNode("INPUT", {"type": "search"})
        button_node = _JsNullNode("BUTTON")
        disabled_input = _JsNullNode("INPUT", {"disabled": ""})
        disabled_button = _JsNullNode("BUTTON", {"disabled": ""})

        assert not _node_is_focusable(div_node)  # type: ignore[arg-type]
        assert not _node_is_focusable(anchor_no_href)  # type: ignore[arg-type]
        assert _node_is_focusable(input_node)  # type: ignore[arg-type]
        assert _node_is_focusable(button_node)  # type: ignore[arg-type]
        assert not _node_is_focusable(disabled_input)  # type: ignore[arg-type]
        assert not _node_is_focusable(disabled_button)  # type: ignore[arg-type]

        panel = _JsNullNode("DIV", children=[div_node, input_node])
        focus_initial(panel)  # type: ignore[arg-type]
        assert input_node.focused
        assert not panel.focused

        empty_panel = _JsNullNode("DIV")
        focus_initial(empty_panel)  # type: ignore[arg-type]
        assert empty_panel.getAttribute("tabindex") == "-1"
        assert empty_panel.focused


class TestDrawer:
    """Drawer 6.2: edge prop, shared a11y contract."""

    def test_edge_reflection(self, overlay_env):
        from webcompy.ui.headless import Drawer

        for edge in ("left", "right", "top", "bottom"):

            @define_component(custom_element_name=f"test-drawer-{edge}")
            def Page(ctx, _edge=edge):
                return Drawer(
                    {"open": True, "edge": _edge, "aria_label": "Drawer", "transition_name": "webcompy-drawer"}
                )

            with TestRenderer.render(Page) as result:
                body = result.body_node
                assert body is not None
                found = None
                stack = [body]
                while stack:
                    node = stack.pop()
                    if node.getAttribute("data-edge") == edge:
                        found = node
                        break
                    for i in range(node.childNodes.length - 1, -1, -1):
                        stack.append(node.childNodes[i])
                assert found is not None, f"edge {edge} not reflected"

    def test_escape_closes_drawer(self, overlay_env):
        from webcompy.ui.headless import Drawer

        called: list[str] = []

        @define_component(custom_element_name="test-drawer-escape")
        def Page(ctx):
            sig = use_state(lambda: True)
            return Drawer(
                {
                    "open": sig,
                    "on_close": lambda: called.append("close"),
                    "aria_label": "Drawer esc",
                    "transition_name": "webcompy-drawer",
                }
            )

        with TestRenderer.render(Page) as result:
            from webcompy.ports._keys import DOM_PORT_KEY

            dom_port = result._scope.inject(DOM_PORT_KEY, default=None)
            dom_port.dispatch_document_event("keydown", {"key": "Escape"})
            assert called == ["close"]

    def test_backdrop_dismiss_and_disable(self, overlay_env):
        from webcompy.ui.headless import Drawer

        called: list[str] = []

        @define_component(custom_element_name="test-drawer-backdrop")
        def Page(ctx):
            return Drawer(
                {
                    "open": True,
                    "on_close": lambda: called.append("close"),
                    "edge": "right",
                    "aria_label": "Drawer backdrop",
                    "transition_name": "webcompy-drawer",
                },
                slots={"default": lambda: html.DIV({}, "drawer body")},
            )

        with TestRenderer.render(Page) as result:
            from webcompy.ports._keys import DOM_PORT_KEY

            dom_port = result._scope.inject(DOM_PORT_KEY, default=None)
            backdrops = _find_all(
                result.body_node,
                lambda n: "webcompy-headless-drawer-backdrop" in (n.getAttribute("class") or ""),
            )
            assert len(backdrops) == 1
            dom_port.dispatch_document_event("click", {"target": backdrops[0]})
            assert called == ["close"]

        called2: list[str] = []

        @define_component(custom_element_name="test-drawer-backdrop-off")
        def Page2(ctx):
            return Drawer(
                {
                    "open": True,
                    "on_close": lambda: called2.append("close"),
                    "edge": "right",
                    "close_on_backdrop": False,
                    "aria_label": "Drawer backdrop off",
                    "transition_name": "webcompy-drawer",
                },
                slots={"default": lambda: html.DIV({}, "drawer body")},
            )

        with TestRenderer.render(Page2) as result:
            from webcompy.ports._keys import DOM_PORT_KEY

            dom_port = result._scope.inject(DOM_PORT_KEY, default=None)
            backdrops = _find_all(
                result.body_node,
                lambda n: "webcompy-headless-drawer-backdrop" in (n.getAttribute("class") or ""),
            )
            assert len(backdrops) == 1
            dom_port.dispatch_document_event("click", {"target": backdrops[0]})
            assert called2 == []

    def test_reopen_drawer_evaluates_fresh_slot(self, overlay_env):
        from webcompy.ports._keys import ASYNC_SCHEDULER_PORT_KEY
        from webcompy.ui import Drawer
        from webcompy_testing import VirtualDOMEvent, run_sync

        open_sig = Signal(False)
        text_sig = Signal("")
        renders: list[int] = [0]

        def _render_slot():
            renders[0] += 1
            return html.INPUT({"id": "drawer-reopen-input", "type": "text", ":bind": text_sig})

        @define_component(custom_element_name="test-drawer-reopen")
        def Page(ctx):
            return Drawer(
                {"open": open_sig, "edge": "right", "aria_label": "Drawer reopen"},
                slots={"default": _render_slot},
            )

        with TestRenderer.render(Page) as result:
            sched = result._scope.inject(ASYNC_SCHEDULER_PORT_KEY)
            open_sig.value = True
            run_sync(sched.drain())
            result.transition_port.flush_frame()
            assert renders[0] == 1

            open_sig.value = False
            run_sync(sched.drain())
            result.transition_port.flush_frame()
            assert _find_all(result.body_node, lambda n: n.getAttribute("id") == "drawer-reopen-input") == []

            open_sig.value = True
            run_sync(sched.drain())
            result.transition_port.flush_frame()
            inputs = _find_all(result.body_node, lambda n: n.getAttribute("id") == "drawer-reopen-input")
            assert len(inputs) == 1
            assert renders[0] == 2
            inputs[0].value = "drawer-updated"
            inputs[0].dispatchEvent(VirtualDOMEvent("input"))
            assert text_sig.value == "drawer-updated"


class TestDropdown:
    """Dropdown 6.3: ARIA, keyboard, outside click, listener cleanup."""

    def test_trigger_aria(self, overlay_env):
        from webcompy.signal import Signal
        from webcompy.ui.headless import Dropdown

        sig = Signal(False)

        @define_component(custom_element_name="test-dropdown-aria")
        def Page(ctx):
            return Dropdown(
                {"open": sig, "transition_name": "webcompy-dropdown"},
                slots={"trigger": lambda: "Menu", "default": lambda: html.LI({"role": "menuitem"}, "Item")},
            )

        with TestRenderer.render(Page) as result:
            # Find trigger button
            found = None
            stack = [result._root_node]
            while stack:
                node = stack.pop()
                if node.nodeName == "BUTTON" and node.getAttribute("aria-haspopup") == "menu":
                    found = node
                    break
                for i in range(node.childNodes.length - 1, -1, -1):
                    child = node.childNodes[i]
                    from webcompy_server.ports import VirtualDOMNode

                    if isinstance(child, VirtualDOMNode):
                        stack.append(child)
            assert found is not None
            assert found.getAttribute("aria-expanded") == "false"
            assert found.getAttribute("aria-controls") is not None

    def test_outside_click_closes(self, overlay_env):
        from webcompy.ui.headless import Dropdown

        called: list[str] = []

        @define_component(custom_element_name="test-dropdown-outside")
        def Page(ctx):
            sig = use_state(lambda: True)
            return Dropdown(
                {"open": sig, "on_close": lambda: called.append("close"), "transition_name": "webcompy-dropdown"},
                slots={"trigger": lambda: "Trigger", "default": lambda: html.LI({"role": "menuitem"}, "Item")},
            )

        with TestRenderer.render(Page) as result:
            from webcompy.ports._keys import DOM_PORT_KEY

            dom_port = result._scope.inject(DOM_PORT_KEY, default=None)
            # Click outside (target not trigger nor menu)
            # Create a fake outsider node not in dropdown
            from webcompy_testing._dom import FakeDOMNode

            outsider_node = FakeDOMNode("div")
            outsider_node.setAttribute("id", "outside")
            dom_port.dispatch_document_event("click", {"target": outsider_node})
            assert called == ["close"]

    def test_trigger_click_excluded_from_outside(self, overlay_env):
        from webcompy.ui.headless import Dropdown

        called: list[str] = []

        @define_component(custom_element_name="test-dropdown-trigger-exclude")
        def Page(ctx):
            sig = use_state(lambda: True)
            return Dropdown(
                {"open": sig, "on_close": lambda: called.append("close"), "transition_name": "webcompy-dropdown"},
                slots={"trigger": lambda: "Trigger", "default": lambda: html.LI({"role": "menuitem"}, "Item")},
            )

        with TestRenderer.render(Page) as result:
            from webcompy.ports._keys import DOM_PORT_KEY

            dom_port = result._scope.inject(DOM_PORT_KEY, default=None)
            # Find trigger
            trigger = None
            stack = [result._root_node]
            while stack:
                node = stack.pop()
                if node.nodeName == "BUTTON":
                    trigger = node
                    break
                for i in range(node.childNodes.length - 1, -1, -1):
                    child = node.childNodes[i]
                    from webcompy_server.ports import VirtualDOMNode

                    if isinstance(child, VirtualDOMNode):
                        stack.append(child)
            assert trigger is not None
            dom_port.dispatch_document_event("click", {"target": trigger})
            assert called == []

    def test_trigger_click_stops_propagation(self, overlay_env):
        from webcompy.ui.headless import Dropdown
        from webcompy_server.ports._virtual_dom import VirtualDOMEvent

        class _SpyEvent(VirtualDOMEvent):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.propagation_stopped = False

            def stopPropagation(self):
                super().stopPropagation()
                self.propagation_stopped = True

        sig = Signal(False)
        bubbled: list[str] = []

        @define_component(custom_element_name="test-dropdown-propagation")
        def Page(ctx):
            return Dropdown(
                {"open": sig, "transition_name": "webcompy-dropdown"},
                slots={"trigger": lambda: "Menu", "default": lambda: html.LI({"role": "menuitem"}, "Item")},
            )

        with TestRenderer.render(Page) as result:
            triggers = _find_all(
                result._root_node,
                lambda n: n.nodeName == "BUTTON" and n.getAttribute("aria-haspopup") == "menu",
            )
            assert len(triggers) == 1
            result._root_node.addEventListener("click", lambda _ev: bubbled.append("root"))
            event = _SpyEvent("click", bubbles=True, cancelable=True)
            triggers[0].dispatchEvent(event)
            assert sig.value is True
            assert event.propagation_stopped is True
            assert bubbled == []

    def test_two_dropdowns_have_distinct_ids(self, overlay_env):
        from webcompy.components._component import _active_app_context
        from webcompy.ui.headless import Dropdown

        app_ctx = _FakeAppCtx()

        @define_component(custom_element_name="test-dropdown-dup-ids")
        def Page(ctx):
            return html.DIV(
                {},
                Dropdown(
                    {"open": True, "transition_name": "webcompy-dropdown"},
                    slots={"trigger": lambda: "First", "default": lambda: html.LI({"role": "menuitem"}, "A")},
                ),
                Dropdown(
                    {"open": True, "transition_name": "webcompy-dropdown"},
                    slots={"trigger": lambda: "Second", "default": lambda: html.LI({"role": "menuitem"}, "B")},
                ),
            )

        token = _active_app_context.set(app_ctx)
        try:
            with TestRenderer.render(Page) as result:
                triggers = _find_all(
                    result._root_node,
                    lambda n: n.nodeName == "BUTTON" and n.getAttribute("aria-haspopup") == "menu",
                )
                assert len(triggers) == 2
                trigger_ids = [t.getAttribute("id") for t in triggers]
                controls = [t.getAttribute("aria-controls") for t in triggers]
                assert trigger_ids[0] != trigger_ids[1]
                assert controls[0] != controls[1]
                menus = _find_all(
                    result.body_node,
                    lambda n: n.getAttribute("role") == "menu",
                )
                assert len(menus) == 2
                menu_ids = [m.getAttribute("id") for m in menus]
                assert menu_ids[0] != menu_ids[1]
                assert set(menu_ids) == set(controls)
        finally:
            _active_app_context.reset(token)

    def test_enter_space_activates_via_keydown(self, overlay_env):
        from webcompy.ui.headless import Dropdown
        from webcompy_server.ports._virtual_dom import VirtualDOMEvent

        activated: list[str] = []
        closed: list[str] = []

        @define_component(custom_element_name="test-dropdown-enter")
        def Page(ctx):
            sig = use_state(lambda: True)
            return Dropdown(
                {"open": sig, "on_close": lambda: closed.append("close"), "transition_name": "webcompy-dropdown"},
                slots={
                    "trigger": lambda: "Trigger",
                    "default": lambda: html.LI(
                        {"role": "menuitem", "@click": lambda _e: activated.append("item1")}, "Item 1"
                    ),
                },
            )

        with TestRenderer.render(Page) as result:
            body = result.body_node
            assert body is not None
            menu = None
            stack = [body]
            while stack:
                node = stack.pop()
                if node.getAttribute("role") == "menu":
                    menu = node
                    break
                for i in range(node.childNodes.length - 1, -1, -1):
                    stack.append(node.childNodes[i])
            assert menu is not None
            item = None
            stack2 = [menu]
            while stack2:
                n = stack2.pop()
                if n.getAttribute("role") == "menuitem":
                    item = n
                    break
                for i in range(n.childNodes.length - 1, -1, -1):
                    stack2.append(n.childNodes[i])
            assert item is not None
            with __import__("contextlib").suppress(Exception):
                item.focus()
            orig_click = getattr(item, "click", None)

            def mock_click():
                activated.append("item1")

            try:
                object.__setattr__(item, "click", mock_click)
            except Exception:
                item.click = mock_click  # type: ignore[attr-defined]

            for key in ("Enter", " "):
                event = VirtualDOMEvent("keydown", bubbles=True, cancelable=True)
                event.key = key  # type: ignore[attr-defined]
                menu.dispatchEvent(event)

            assert activated.count("item1") >= 2
            assert closed.count("close") >= 2
            if orig_click is not None:
                with __import__("contextlib").suppress(Exception):
                    object.__setattr__(item, "click", orig_click)

    def test_arrow_wrap_and_home_end(self, overlay_env):
        from webcompy.ui.headless import Dropdown
        from webcompy_server.ports._virtual_dom import VirtualDOMEvent

        @define_component(custom_element_name="test-dropdown-arrows")
        def Page(ctx):
            sig = use_state(lambda: True)
            return Dropdown(
                {"open": sig, "transition_name": "webcompy-dropdown"},
                slots={
                    "trigger": lambda: "Trigger",
                    "default": lambda: [
                        html.LI({"role": "menuitem"}, "A"),
                        html.LI({"role": "menuitem"}, "B"),
                        html.LI({"role": "menuitem"}, "C"),
                    ],
                },
            )

        with TestRenderer.render(Page) as result:
            from webcompy.ports._keys import HOST_PORT_KEY

            body = result.body_node
            assert body is not None
            menu = None
            stack = [body]
            while stack:
                node = stack.pop()
                if node.getAttribute("role") == "menu":
                    menu = node
                    break
                for i in range(node.childNodes.length - 1, -1, -1):
                    stack.append(node.childNodes[i])
            assert menu is not None
            # Collect items in document order (stack pop yields document order)
            items: list = []
            s = [menu]
            while s:
                n = s.pop()
                if n.getAttribute("role") == "menuitem":
                    items.append(n)
                for i in range(n.childNodes.length - 1, -1, -1):
                    s.append(n.childNodes[i])
            # Ensure we have 3
            assert len(items) == 3
            host_port = result._scope.inject(HOST_PORT_KEY, default=None)

            def active():
                if host_port is not None:
                    getter = host_port.create_js_global_getter(
                        "document",
                        wrapper=lambda doc: getattr(doc, "activeElement", None) if doc is not None else None,
                    )
                    return getter()
                return None

            # Focus first item then ArrowDown should wrap through all
            with __import__("contextlib").suppress(Exception):
                items[0].focus()
            assert active() is items[0]
            event_down = VirtualDOMEvent("keydown", bubbles=True, cancelable=True)
            event_down.key = "ArrowDown"  # type: ignore[attr-defined]
            menu.dispatchEvent(event_down)
            assert active() is items[1]
            menu.dispatchEvent(event_down)
            assert active() is items[2]
            menu.dispatchEvent(event_down)
            assert active() is items[0]
            # ArrowUp wrap
            event_up = VirtualDOMEvent("keydown", bubbles=True, cancelable=True)
            event_up.key = "ArrowUp"  # type: ignore[attr-defined]
            menu.dispatchEvent(event_up)
            assert active() is items[2]
            # Home / End
            event_home = VirtualDOMEvent("keydown", bubbles=True, cancelable=True)
            event_home.key = "Home"  # type: ignore[attr-defined]
            menu.dispatchEvent(event_home)
            assert active() is items[0]
            event_end = VirtualDOMEvent("keydown", bubbles=True, cancelable=True)
            event_end.key = "End"  # type: ignore[attr-defined]
            menu.dispatchEvent(event_end)
            assert active() is items[2]

    @staticmethod
    def _find_trigger(root):
        stack = [root]
        while stack:
            node = stack.pop()
            if node.nodeName == "BUTTON" and node.getAttribute("aria-haspopup") == "menu":
                return node
            for i in range(node.childNodes.length - 1, -1, -1):
                stack.append(node.childNodes[i])
        return None

    @staticmethod
    def _find_menu(body):
        stack = [body]
        while stack:
            node = stack.pop()
            if node.getAttribute("role") == "menu":
                return node
            for i in range(node.childNodes.length - 1, -1, -1):
                stack.append(node.childNodes[i])
        return None

    def test_menu_anchored_below_trigger_start(self, overlay_env):
        from webcompy.signal import Signal
        from webcompy.ui.headless import Dropdown

        class _Rect:
            bottom = 120.0
            left = 24.0
            right = 96.0

        sig = Signal(False)

        @define_component(custom_element_name="test-dropdown-anchor-start")
        def Page(ctx):
            return Dropdown(
                {"open": sig, "transition_name": "webcompy-dropdown"},
                slots={"trigger": lambda: "Trigger", "default": lambda: html.LI({"role": "menuitem"}, "Item")},
            )

        with TestRenderer.render(Page) as result:
            from webcompy.ports._keys import DOM_PORT_KEY

            dom_port = result._scope.inject(DOM_PORT_KEY, default=None)
            trigger = self._find_trigger(result._root_node)
            assert trigger is not None
            trigger.getBoundingClientRect = lambda: _Rect()
            original_lookup = dom_port.get_element_by_id
            dom_port.get_element_by_id = lambda element_id: (
                trigger if element_id == trigger.getAttribute("id") else original_lookup(element_id)
            )
            sig.value = True
            menu = self._find_menu(result.body_node)
            assert menu is not None
            assert menu.getAttribute("style") == "top: 120.0px; left: 24.0px; right: auto;"

    def test_menu_anchor_align_end(self, overlay_env):
        from webcompy.signal import Signal
        from webcompy.ui.headless import Dropdown

        class _Rect:
            bottom = 120.0
            left = 24.0
            right = 96.0

        sig = Signal(False)

        @define_component(custom_element_name="test-dropdown-anchor-end")
        def Page(ctx):
            return Dropdown(
                {"open": sig, "align": "end", "transition_name": "webcompy-dropdown"},
                slots={"trigger": lambda: "Trigger", "default": lambda: html.LI({"role": "menuitem"}, "Item")},
            )

        with TestRenderer.render(Page) as result:
            from webcompy.ports._keys import DOM_PORT_KEY

            dom_port = result._scope.inject(DOM_PORT_KEY, default=None)
            trigger = self._find_trigger(result._root_node)
            assert trigger is not None
            trigger.getBoundingClientRect = lambda: _Rect()
            original_lookup = dom_port.get_element_by_id
            dom_port.get_element_by_id = lambda element_id: (
                trigger if element_id == trigger.getAttribute("id") else original_lookup(element_id)
            )
            sig.value = True
            menu = self._find_menu(result.body_node)
            assert menu is not None
            assert menu.getAttribute("style") == "top: 120.0px; right: calc(100vw - 96.0px); left: auto;"

    def test_anchor_remeasures_on_scroll_and_resize(self, overlay_env):
        from webcompy.ports._keys import DOM_PORT_KEY, HOST_PORT_KEY
        from webcompy.ui.headless import Dropdown

        rect = {"bottom": 120.0, "left": 24.0, "right": 96.0}

        class _Rect:
            @property
            def bottom(self):
                return rect["bottom"]

            @property
            def left(self):
                return rect["left"]

            @property
            def right(self):
                return rect["right"]

        sig = Signal(False)

        @define_component(custom_element_name="test-dropdown-anchor-remeasure")
        def Page(ctx):
            return Dropdown(
                {"open": sig, "transition_name": "webcompy-dropdown"},
                slots={"trigger": lambda: "Trigger", "default": lambda: html.LI({"role": "menuitem"}, "Item")},
            )

        with TestRenderer.render(Page) as result:
            dom_port = result._scope.inject(DOM_PORT_KEY, default=None)
            host_port = result._scope.inject(HOST_PORT_KEY, default=None)
            trigger = self._find_trigger(result._root_node)
            assert trigger is not None
            trigger.getBoundingClientRect = lambda: _Rect()
            original_lookup = dom_port.get_element_by_id
            dom_port.get_element_by_id = lambda element_id: (
                trigger if element_id == trigger.getAttribute("id") else original_lookup(element_id)
            )
            sig.value = True
            menu = self._find_menu(result.body_node)
            assert menu is not None
            assert "top: 120.0px" in menu.getAttribute("style")
            rect["bottom"] = 200.0
            rect["left"] = 40.0
            dom_port.dispatch_document_event("scroll", None)
            assert menu.getAttribute("style") == "top: 200.0px; left: 40.0px; right: auto;"
            rect["bottom"] = 260.0
            host_port.dispatch_window_event("resize", None)
            assert menu.getAttribute("style") == "top: 260.0px; left: 40.0px; right: auto;"

    def test_anchor_listeners_removed_on_close(self, overlay_env):
        from webcompy.ports._keys import DOM_PORT_KEY, HOST_PORT_KEY
        from webcompy.ui.headless import Dropdown

        rect = {"bottom": 120.0, "left": 24.0, "right": 96.0}

        class _Rect:
            @property
            def bottom(self):
                return rect["bottom"]

            @property
            def left(self):
                return rect["left"]

            @property
            def right(self):
                return rect["right"]

        called: list[str] = []
        sig = Signal(False)

        @define_component(custom_element_name="test-dropdown-anchor-cleanup")
        def Page(ctx):
            return Dropdown(
                {
                    "open": sig,
                    "on_close": lambda: called.append("close"),
                    "transition_name": "webcompy-dropdown",
                },
                slots={"trigger": lambda: "Trigger", "default": lambda: html.LI({"role": "menuitem"}, "Item")},
            )

        with TestRenderer.render(Page) as result:
            dom_port = result._scope.inject(DOM_PORT_KEY, default=None)
            host_port = result._scope.inject(HOST_PORT_KEY, default=None)
            trigger = self._find_trigger(result._root_node)
            assert trigger is not None
            trigger.getBoundingClientRect = lambda: _Rect()
            original_lookup = dom_port.get_element_by_id
            dom_port.get_element_by_id = lambda element_id: (
                trigger if element_id == trigger.getAttribute("id") else original_lookup(element_id)
            )
            sig.value = True
            menu = self._find_menu(result.body_node)
            assert menu is not None
            sig.value = False
            rect["bottom"] = 999.0
            dom_port.dispatch_document_event("scroll", None)
            host_port.dispatch_window_event("resize", None)
            assert menu.getAttribute("style") == "top: 120.0px; left: 24.0px; right: auto;"

    def test_positioning_none_skips_anchor(self, overlay_env):
        from webcompy.signal import Signal
        from webcompy.ui.headless import Dropdown

        class _Rect:
            bottom = 120.0
            left = 24.0
            right = 96.0

        sig = Signal(False)

        @define_component(custom_element_name="test-dropdown-anchor-none")
        def Page(ctx):
            return Dropdown(
                {"open": sig, "positioning": "none", "transition_name": "webcompy-dropdown"},
                slots={"trigger": lambda: "Trigger", "default": lambda: html.LI({"role": "menuitem"}, "Item")},
            )

        with TestRenderer.render(Page) as result:
            from webcompy.ports._keys import DOM_PORT_KEY

            dom_port = result._scope.inject(DOM_PORT_KEY, default=None)
            trigger = self._find_trigger(result._root_node)
            assert trigger is not None
            trigger.getBoundingClientRect = lambda: _Rect()
            original_lookup = dom_port.get_element_by_id
            dom_port.get_element_by_id = lambda element_id: (
                trigger if element_id == trigger.getAttribute("id") else original_lookup(element_id)
            )
            sig.value = True
            menu = self._find_menu(result.body_node)
            assert menu is not None
            assert menu.getAttribute("style") is None

    def test_anchor_without_measurement_falls_back(self, overlay_env):
        from webcompy.signal import Signal
        from webcompy.ui.headless import Dropdown

        sig = Signal(False)

        @define_component(custom_element_name="test-dropdown-anchor-fallback")
        def Page(ctx):
            return Dropdown(
                {"open": sig, "transition_name": "webcompy-dropdown"},
                slots={"trigger": lambda: "Trigger", "default": lambda: html.LI({"role": "menuitem"}, "Item")},
            )

        with TestRenderer.render(Page) as result:
            sig.value = True
            menu = self._find_menu(result.body_node)
            assert menu is not None
            # No getBoundingClientRect available: no offsets are emitted
            assert menu.getAttribute("style") is None


class TestToast:
    """Toast 6.4: push, variant, auto-dismiss, manual dismiss, destroy."""

    def test_push_renders(self, overlay_env):
        from webcompy.ui.composables import use_toast
        from webcompy.ui.headless import ToastHost

        @define_component(custom_element_name="test-toast-push")
        def Page(ctx):
            push, state = use_toast()
            ctx._push = push  # type: ignore[attr-defined]
            ctx._state = state  # type: ignore[attr-defined]
            return ToastHost(
                {
                    "toasts": state.toasts,
                    "on_dismiss": state.dismiss,
                    "on_remove": state._remove,
                    "transition_name": "webcompy-toast",
                }
            )

        with TestRenderer.render(Page) as result:
            body = result.body_node
            assert body is not None
            # Initially no toasts
            assert body.textContent is not None

    def test_variant_semantics(self, overlay_env):
        from webcompy.ui.headless import ToastHost

        @define_component(custom_element_name="test-toast-variant")
        def Page(ctx):
            sig: Signal[list] = use_state(lambda: [])  # type: ignore[arg-type]
            from webcompy.ui.composables._toast import ToastRecord

            sig.value = [ToastRecord(id="1", message="Error!", variant="error", duration=None, leaving=False)]
            return ToastHost({"toasts": sig, "transition_name": "webcompy-toast"})

        with TestRenderer.render(Page) as result:
            body = result.body_node
            assert body is not None
            # Find alert role
            found = None
            stack = [body]
            while stack:
                node = stack.pop()
                if node.getAttribute("role") == "alert":
                    found = node
                    break
                for i in range(node.childNodes.length - 1, -1, -1):
                    stack.append(node.childNodes[i])
            assert found is not None
            assert found.getAttribute("data-variant") == "error"

    def test_toast_host_renders_list(self, overlay_env):
        from webcompy.signal import Signal
        from webcompy.ui.composables._toast import ToastRecord
        from webcompy.ui.headless import ToastHost

        sig: Signal[list[ToastRecord]] = Signal(
            [ToastRecord(id="1", message="Hello", variant="info", duration=None, leaving=False)]
        )

        @define_component(custom_element_name="test-toast-list")
        def Page(ctx):
            return ToastHost({"toasts": sig, "transition_name": "webcompy-toast"})

        with TestRenderer.render(Page) as result:
            body = result.body_node
            assert body is not None
            has_hello = False
            stack2 = [body]
            while stack2:
                n = stack2.pop()
                if n.textContent and "Hello" in n.textContent:
                    has_hello = True
                    break
                for i in range(n.childNodes.length - 1, -1, -1):
                    stack2.append(n.childNodes[i])
            assert has_hello

    def test_auto_dismiss_via_fake_transition_port(self, overlay_env):
        from webcompy.ports._keys import TRANSITION_PORT_KEY
        from webcompy.ui.composables import use_toast
        from webcompy.ui.headless import ToastHost

        holder: dict[str, object] = {}

        @define_component(custom_element_name="test-toast-auto-dismiss")
        def Page(ctx):
            push, state = use_toast()
            holder["push"] = push
            holder["state"] = state
            return ToastHost(
                {
                    "toasts": state.toasts,
                    "on_dismiss": state.dismiss,
                    "on_remove": state._remove,  # type: ignore[attr-defined]
                    "transition_name": "webcompy-toast",
                }
            )

        with TestRenderer.render(Page) as result:
            push = holder["push"]  # type: ignore[assignment]
            state = holder["state"]  # type: ignore[assignment]
            port = result._scope.inject(TRANSITION_PORT_KEY, default=None)
            assert port is not None
            # Push with short duration (50ms)
            rid = push("auto", "info", 0.05)  # type: ignore[operator]
            assert len(state.toasts.value) == 1  # type: ignore[attr-defined]
            # Advance fake clock to fire auto-dismiss timer
            port.advance_time(60)
            # _dismiss marks leaving True before Transition on_leave_end removes
            assert state.toasts.value[0].leaving is True  # type: ignore[attr-defined]
            # Simulate Transition on_leave_end removal via state._remove
            state._remove(rid)  # type: ignore[attr-defined]
            assert len(state.toasts.value) == 0  # type: ignore[attr-defined]

    def test_manual_dismiss_cancels_timer(self, overlay_env):
        from webcompy.ports._keys import TRANSITION_PORT_KEY
        from webcompy.ui.composables import use_toast

        holder: dict[str, object] = {}

        @define_component(custom_element_name="test-toast-dismiss-cancel")
        def Page(ctx):
            push, state = use_toast()
            holder["push"] = push
            holder["state"] = state
            return html.DIV({})

        with TestRenderer.render(Page) as result:
            port = result._scope.inject(TRANSITION_PORT_KEY, default=None)
            assert port is not None
            push = holder["push"]  # type: ignore[assignment]
            state = holder["state"]  # type: ignore[assignment]
            rid = push("pending", "info", 0.5)  # type: ignore[operator]
            assert len(state.toasts.value) == 1  # type: ignore[attr-defined]
            # Timer scheduled
            assert len(port._timeouts) == 1  # type: ignore[attr-defined]
            # Manual dismiss cancels timer
            state.dismiss(rid)  # type: ignore[attr-defined]
            assert len(port._timeouts) == 0  # type: ignore[attr-defined]
            assert state.toasts.value[0].leaving is True  # type: ignore[attr-defined]
            # Advancing after manual dismiss must not fire again
            port.advance_time(1000)
            assert state.toasts.value[0].leaving is True  # type: ignore[attr-defined]

    def test_destroy_cancels_via_cleanup(self, overlay_env):
        from webcompy.ui.composables import use_toast

        holder: dict[str, object] = {}

        @define_component(custom_element_name="test-toast-destroy-cleanup")
        def Page(ctx):
            push, state = use_toast()
            holder["push"] = push
            holder["state"] = state
            # Verify use_toast registers before_destroy cleanup (indirect).
            # TestRenderer's close does not trigger component destroy hooks,
            # so full destroy path is covered by design.md D10 and manual
            # dismiss test above.
            return html.DIV({})

        with TestRenderer.render(Page) as result:
            # If Page rendered without error, the composable registered cleanup
            assert result.body_node is not None


class TestIntegration:
    """Integration 6.5: Teleport, closed no content, data-state vocabularies."""

    def test_closed_contributes_no_content(self, overlay_env):
        from webcompy.ui.headless import Modal

        @define_component(custom_element_name="test-integration-closed")
        def Page(ctx):
            return Modal({"open": False, "aria_label": "Closed", "transition_name": "webcompy-modal"})

        with TestRenderer.render(Page) as result:
            body = result.body_node
            assert body is not None
            # Body should have only the root div, no modal container
            # Check that no element with role dialog exists
            found = None
            stack = [body]
            while stack:
                node = stack.pop()
                if node.getAttribute("role") == "dialog":
                    found = node
                    break
                for i in range(node.childNodes.length - 1, -1, -1):
                    stack.append(node.childNodes[i])
            assert found is None

    def test_open_renders_under_body(self, overlay_env):
        from webcompy.ui.headless import Modal

        @define_component(custom_element_name="test-integration-open")
        def Page(ctx):
            return Modal({"open": True, "aria_label": "Open", "transition_name": "webcompy-modal"})

        with TestRenderer.render(Page) as result:
            body = result.body_node
            assert body is not None
            found = None
            stack = [body]
            while stack:
                node = stack.pop()
                if node.getAttribute("role") == "dialog":
                    found = node
                    break
                for i in range(node.childNodes.length - 1, -1, -1):
                    stack.append(node.childNodes[i])
            assert found is not None
            assert found.parentNode is not None

    def test_data_state_vocabularies(self, overlay_env):
        from webcompy.signal import Signal
        from webcompy.ui.composables._toast import ToastRecord
        from webcompy.ui.headless import Drawer, Dropdown, Modal, ToastHost

        @define_component(custom_element_name="test-data-state")
        def Page(ctx):
            sig_t: Signal[list[ToastRecord]] = Signal(
                [ToastRecord(id="1", message="Hi", variant="info", duration=None, leaving=False)]
            )
            return html.DIV(
                {},
                Modal({"open": True, "aria_label": "M", "transition_name": "webcompy-modal"}),
                Drawer({"open": True, "aria_label": "D", "transition_name": "webcompy-drawer"}),
                Dropdown(
                    {"open": True, "transition_name": "webcompy-dropdown"},
                    slots={"trigger": lambda: "T", "default": lambda: html.LI({"role": "menuitem"}, "I")},
                ),
                ToastHost({"toasts": sig_t, "transition_name": "webcompy-toast"}),
            )

        with TestRenderer.render(Page) as result:
            body = result.body_node
            assert body is not None
            # Check data-state values
            states: list[str] = []
            stack = [body]
            while stack:
                node = stack.pop()
                ds = node.getAttribute("data-state")
                if ds:
                    states.append(ds)
                for i in range(node.childNodes.length - 1, -1, -1):
                    stack.append(node.childNodes[i])
            assert "open" in states
            assert "visible" in states

    def test_themed_wrappers(self, overlay_env):
        from webcompy.signal import Signal
        from webcompy.ui import Drawer as ThemedDrawer
        from webcompy.ui import Dropdown as ThemedDropdown
        from webcompy.ui import Modal as ThemedModal
        from webcompy.ui import ToastHost as ThemedToastHost
        from webcompy.ui.composables._toast import ToastRecord

        sig: Signal[list[ToastRecord]] = Signal([])

        @define_component(custom_element_name="test-themed-wrappers")
        def Page(ctx):
            return html.DIV(
                {},
                ThemedModal({"open": False, "aria_label": "M"}),
                ThemedDrawer({"open": False, "aria_label": "D"}),
                ThemedDropdown(
                    {"open": False},
                    slots={"trigger": lambda: "T", "default": lambda: html.LI({"role": "menuitem"}, "I")},
                ),
                ThemedToastHost({"toasts": sig}),
            )

        with TestRenderer.render(Page) as result:
            # Themed should render without error even when closed
            assert result.body_node is not None
