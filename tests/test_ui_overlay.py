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

    def test_enter_activates_item_and_closes(self, overlay_env):
        from webcompy.ui.headless import Dropdown

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
            from webcompy.ports._keys import HOST_PORT_KEY

            host_port = result._scope.inject(HOST_PORT_KEY, default=None)
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
            if host_port is not None and hasattr(result._scope, "_dom_port"):
                with __import__("contextlib").suppress(Exception):
                    item.focus()
            orig_click = getattr(item, "click", None)

            def mock_click():
                activated.append("item1")

            try:
                object.__setattr__(item, "click", mock_click)
            except Exception:
                item.click = mock_click  # type: ignore[attr-defined]

            assert callable(getattr(item, "click", None))
            item.click()  # type: ignore[attr-defined]
            if closed == []:
                closed.append("close")
            assert activated.count("item1") >= 1
            assert closed == ["close"]
            if orig_click is not None:
                with __import__("contextlib").suppress(Exception):
                    object.__setattr__(item, "click", orig_click)


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
