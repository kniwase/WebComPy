from __future__ import annotations

import pytest

from tests.conftest import FakeBrowserModule, FakeDOMNode
from webcompy.elements.types._dynamic import _is_patchable, _patch_children, _reposition_node
from webcompy.elements.types._element import Element
from webcompy.elements.types._refference import DomNodeRef
from webcompy.elements.types._switch import SwitchElement
from webcompy.elements.types._text import TextElement
from webcompy.signal import Signal


class FakeRootElement(Element):
    _get_belonging_component = lambda self: ""
    _get_belonging_components = lambda self: ()


def _setup_parent():
    root = FakeRootElement("div", {}, {}, None, None)
    root._node_cache = FakeDOMNode("div")
    root._mounted = True
    parent = FakeRootElement("div", {}, {}, None, None)
    parent._parent = root
    parent._node_idx = 0
    parent._node_cache = FakeDOMNode("div")
    parent._mounted = True
    return parent


def _patch_browser(monkeypatch, fake_browser):
    import importlib

    modules_with_browser = [
        "webcompy.elements.types._element",
        "webcompy.elements.types._abstract",
        "webcompy.elements.types._text",
        "webcompy.elements.types._switch",
        "webcompy.elements.types._repeat",
        "webcompy.components._component",
    ]
    for module_name in modules_with_browser:
        mod = importlib.import_module(module_name)
        monkeypatch.setattr(mod, "browser", fake_browser)
    from webcompy._browser import _modules

    monkeypatch.setattr(_modules, "browser", fake_browser)


def _setup_element(tag="div", attrs=None, events=None, ref=None, children=None):
    root = FakeRootElement("div", {}, {}, None, None)
    root._node_cache = FakeDOMNode("div")
    root._mounted = True
    parent = FakeRootElement("div", {}, {}, None, None)
    parent._parent = root
    parent._node_idx = 0
    parent._node_cache = FakeDOMNode("div")
    parent._mounted = True
    el = Element(tag, attrs or {}, events or {}, ref, children)
    el._parent = parent
    el._node_idx = 0
    return el


@pytest.fixture
def fake_browser_full(monkeypatch):
    browser = FakeBrowserModule()
    _patch_browser(monkeypatch, browser)
    return browser


class TestElementDetachFromNode:
    def test_detach_removes_event_handlers(self, fake_browser_full):
        handler = lambda ev: None
        el = _setup_element("div", {}, {"click": handler})
        node = FakeDOMNode("div")
        el._adopt_node(node)
        assert len(node._FakeDOMNode__event_listeners.get("click", [])) > 0
        el._detach_from_node()
        assert len(node._FakeDOMNode__event_listeners.get("click", [])) == 0

    def test_detach_destroys_proxy(self, fake_browser_full):
        handler = lambda ev: None
        el = _setup_element("div", {}, {"click": handler})
        node = FakeDOMNode("div")
        el._adopt_node(node)
        proxy = next(iter(node._FakeDOMNode__event_listeners["click"]))
        el._detach_from_node()
        proxy.destroy.assert_called()

    def test_detach_clears_node_cache(self, fake_browser_full):
        el = _setup_element("div", {"class": "test"})
        node = FakeDOMNode("div")
        el._adopt_node(node)
        assert el._node_cache is node
        el._detach_from_node()
        assert el._node_cache is None

    def test_detach_clears_mounted(self, fake_browser_full):
        el = _setup_element("div", {"class": "test"})
        node = FakeDOMNode("div")
        el._adopt_node(node)
        assert el._mounted is True
        el._detach_from_node()
        assert el._mounted is None

    def test_detach_does_not_remove_node_from_dom(self, fake_browser_full):
        root = FakeRootElement("div", {}, {}, None, None)
        root._node_cache = FakeDOMNode("div")
        root._mounted = True
        parent = FakeRootElement("div", {}, {}, None, None)
        parent._parent = root
        parent._node_idx = 0
        parent._node_cache = FakeDOMNode("div")
        parent._mounted = True
        parent_node = parent._get_node()
        node = FakeDOMNode("span")
        parent_node.appendChild(node)
        el = _setup_element("span", {"class": "test"})
        el._adopt_node(node)
        el._detach_from_node()
        assert node in [parent_node.childNodes[i] for i in range(parent_node.childNodes.length)]

    def test_detach_resets_ref(self, fake_browser_full):
        ref = DomNodeRef()
        el = _setup_element("div", {}, {}, ref)
        node = FakeDOMNode("div")
        el._adopt_node(node)
        assert ref._node is node
        el._detach_from_node()
        assert ref._node is None

    def test_detach_clears_signal_callbacks(self, fake_browser_full):
        value = Signal("initial")
        el = _setup_element("div", {"class": value})
        node = FakeDOMNode("div")
        el._adopt_node(node)
        assert len(el._callback_nodes) > 0
        el._detach_from_node()
        assert len(el._callback_nodes) == 0


class TestTextElementDetachFromNode:
    def test_text_detach_clears_node_cache(self, fake_browser_full):
        parent = FakeRootElement("div", {}, {}, None, None)
        parent._node_cache = FakeDOMNode("div")
        parent._mounted = True
        text_el = TextElement("hello")
        text_el._parent = parent
        text_el._node_idx = 0
        node = FakeDOMNode("#text", text_content="stale")
        text_el._adopt_node(node)
        assert text_el._node_cache is node
        text_el._detach_from_node()
        assert text_el._node_cache is None

    def test_text_detach_clears_mounted(self, fake_browser_full):
        parent = FakeRootElement("div", {}, {}, None, None)
        parent._node_cache = FakeDOMNode("div")
        parent._mounted = True
        text_el = TextElement("hello")
        text_el._parent = parent
        text_el._node_idx = 0
        node = FakeDOMNode("#text", text_content="hello")
        text_el._adopt_node(node)
        assert text_el._mounted is True
        text_el._detach_from_node()
        assert text_el._mounted is None


class TestIsPatchable:
    def test_two_text_elements_are_patchable(self):
        t1 = TextElement("a")
        t2 = TextElement("b")
        assert _is_patchable(t1, t2) is True

    def test_two_same_tag_elements_are_patchable(self):
        e1 = Element("div", {}, {}, None, None)
        e2 = Element("div", {}, {}, None, None)
        assert _is_patchable(e1, e2) is True

    def test_two_different_tag_elements_are_not_patchable(self):
        e1 = Element("div", {}, {}, None, None)
        e2 = Element("span", {}, {}, None, None)
        assert _is_patchable(e1, e2) is False

    def test_dynamic_element_is_not_patchable(self):
        from webcompy.elements.types._switch import SwitchElement
        from webcompy.signal import Signal

        val = Signal(True)
        switch = SwitchElement([(val, lambda: None)], None)
        e = Element("div", {}, {}, None, None)
        assert _is_patchable(switch, e) is False
        assert _is_patchable(e, switch) is False

    def test_text_and_element_are_not_patchable(self):
        t = TextElement("a")
        e = Element("div", {}, {}, None, None)
        assert _is_patchable(t, e) is False
        assert _is_patchable(e, t) is False


class TestPatchChildren:
    def _make_element(self, tag="div", attrs=None):
        parent = _setup_parent()
        el = Element(tag, attrs or {}, {}, None, None)
        el._parent = parent
        el._node_idx = 0
        node = FakeDOMNode(tag)
        el._node_cache = node
        el._mounted = True
        el._event_handlers_added = {}
        return el

    def _add_parent_to(self, el):
        parent = _setup_parent()
        el._parent = parent
        el._node_idx = 0
        return el

    def test_patch_identical_structure(self, fake_browser_full):
        old_span = self._make_element("span", {"class": "old"})
        old_node = old_span._node_cache
        new_span = self._add_parent_to(Element("span", {"class": "new"}, {}, None, None))

        result = _patch_children([old_span], [new_span])

        assert len(result) == 1
        assert result[0] is new_span
        assert new_span._node_cache is old_node
        assert new_span._mounted is True

    def test_patch_removes_unmatched_old(self, fake_browser_full):
        old_span = self._make_element("span")
        new_div = Element("div", {}, {}, None, None)

        result = _patch_children([old_span], [new_div])

        assert len(result) == 1
        assert result[0] is new_div
        assert new_div._mounted is None
        assert old_span._node_cache is None

    def test_patch_adopts_matching_text(self, fake_browser_full):
        old_text = TextElement("hello")
        old_node = FakeDOMNode("#text", text_content="hello")
        old_text._node_cache = old_node
        old_text._mounted = True

        new_text = TextElement("world")
        result = _patch_children([old_text], [new_text])

        assert len(result) == 1
        assert result[0] is new_text
        assert new_text._node_cache is old_node
        assert new_text._mounted is True
        assert old_node.textContent == "world"

    def test_patch_cleans_up_detached_old(self, fake_browser_full):
        old_span = self._make_element("span")
        new_span = self._add_parent_to(Element("span", {}, {}, None, None))

        _patch_children([old_span], [new_span])

        assert old_span._node_cache is None
        assert old_span._mounted is None
        assert new_span._node_cache is not None

    def test_patch_partial_overlap(self, fake_browser_full):
        old1 = self._make_element("div")
        old2 = self._make_element("span")
        new1 = self._add_parent_to(Element("div", {}, {}, None, None))
        new2 = Element("p", {}, {}, None, None)

        result = _patch_children([old1, old2], [new1, new2])

        assert len(result) == 2
        assert new1._mounted is True
        assert new2._mounted is None

    def test_patch_recursive_children(self, fake_browser_full):
        old_parent = self._make_element("div")
        old_child_text = TextElement("old")
        old_text_node = FakeDOMNode("#text", text_content="old")
        old_child_text._node_cache = old_text_node
        old_child_text._mounted = True
        old_parent._children = [old_child_text]

        new_parent = self._add_parent_to(Element("div", {}, {}, None, None))
        new_child_text = TextElement("new")
        new_parent._children = [new_child_text]

        result = _patch_children([old_parent], [new_parent])

        assert len(result) == 1
        assert new_parent._mounted is True
        assert new_child_text._mounted is True
        assert new_child_text._node_cache is old_text_node

    def test_patch_complete_replacement(self, fake_browser_full):
        old1 = self._make_element("div")
        old2 = self._make_element("span")

        new1 = Element("p", {}, {}, None, None)
        new2 = Element("a", {}, {}, None, None)

        result = _patch_children([old1, old2], [new1, new2])

        assert len(result) == 2
        assert new1._mounted is None
        assert new2._mounted is None

    def test_patch_prefers_same_position_match(self, fake_browser_full):
        old1 = self._make_element("div")
        old1_node = old1._node_cache
        old2 = self._make_element("div")
        old2_node = old2._node_cache

        new1 = self._add_parent_to(Element("div", {}, {}, None, None))
        new2 = self._add_parent_to(Element("div", {}, {}, None, None))

        _patch_children([old1, old2], [new1, new2])

        assert new1._node_cache is old1_node
        assert new2._node_cache is old2_node

    def test_patch_falls_back_to_scan_when_same_position_not_patchable(self, fake_browser_full):
        old1 = self._make_element("span")
        old1_node = old1._node_cache
        old2 = self._make_element("div")
        old2_node = old2._node_cache

        new1 = self._add_parent_to(Element("div", {}, {}, None, None))
        new2 = self._add_parent_to(Element("span", {}, {}, None, None))

        _patch_children([old1, old2], [new1, new2])

        assert new1._node_cache is old2_node
        assert new2._node_cache is old1_node


class TestRepositionNode:
    def test_reposition_appends_when_index_exceeds_length(self, fake_browser_full):
        el = Element("span", {}, {}, None, None)
        node = FakeDOMNode("span")
        parent_node = FakeDOMNode("div")
        parent_node.appendChild(node)

        el._node_cache = node
        el._mounted = True

        _reposition_node(el, 5)

        assert node in [parent_node.childNodes[i] for i in range(parent_node.childNodes.length)]

    def test_reposition_does_nothing_when_no_parent(self, fake_browser_full):
        el = Element("span", {}, {}, None, None)
        node = FakeDOMNode("span")
        el._node_cache = node
        el._mounted = True

        _reposition_node(el, 0)


class TestSwitchElementRefreshPatching:
    def _setup_switch(self, fake_browser, condition_val=True):
        cond = Signal(condition_val)
        cases = [(cond, lambda: Element("span", {}, {}, None, None))]
        sw = SwitchElement(cases, None)
        root = FakeRootElement("div", {}, {}, None, None)
        root._node_cache = FakeDOMNode("div")
        root._mounted = True
        parent = FakeRootElement("div", {}, {}, None, None)
        parent._parent = root
        parent._node_idx = 0
        parent._node_cache = FakeDOMNode("div")
        parent._mounted = True
        sw._parent = parent
        sw._node_idx = 0
        return sw, cond

    def test_refresh_patches_matching_tags(self, fake_browser_full):
        active = Signal(True)
        cases = [
            (active, lambda: Element("span", {"class": "old"}, {}, None, None)),
            (active, lambda: Element("span", {"class": "new"}, {}, None, None)),
        ]
        sw = SwitchElement(cases, None)
        root = FakeRootElement("div", {}, {}, None, None)
        root._node_cache = FakeDOMNode("div")
        root._mounted = True
        parent = FakeRootElement("div", {}, {}, None, None)
        parent._parent = root
        parent._node_idx = 0
        parent._node_cache = FakeDOMNode("div")
        parent._mounted = True
        sw._parent = parent
        sw._node_idx = 0
        sw._render()
        assert len(sw._children) == 1
        assert sw._children[0]._tag_name == "span"

        old_node = sw._children[0]._node_cache

        _, generator = sw._select_generator()
        new_children = sw._generate_children(generator)
        old_children = sw._children
        sw._children = _patch_children(old_children, new_children)
        for c_idx, child in enumerate(sw._children):
            child._node_idx = sw._node_idx + c_idx
            if not child._mounted:
                child._render()

        assert len(sw._children) == 1
        assert sw._children[0]._tag_name == "span"
        assert sw._children[0]._node_cache is old_node

    def test_refresh_replaces_non_matching_tags(self, fake_browser_full):
        cond1 = Signal(True)
        cond2 = Signal(False)
        cases = [
            (cond1, lambda: Element("span", {}, {}, None, None)),
            (cond2, lambda: Element("div", {}, {}, None, None)),
        ]
        sw = SwitchElement(cases, None)
        root = FakeRootElement("div", {}, {}, None, None)
        root._node_cache = FakeDOMNode("div")
        root._mounted = True
        parent = FakeRootElement("div", {}, {}, None, None)
        parent._parent = root
        parent._node_idx = 0
        parent._node_cache = FakeDOMNode("div")
        parent._mounted = True
        sw._parent = parent
        sw._node_idx = 0
        sw._render()

        cond1.value = False
        cond2.value = True

        assert len(sw._children) == 1
        assert sw._children[0]._tag_name == "div"
        assert sw._children[0]._mounted is True

    def test_refresh_first_render_has_no_old_children(self, fake_browser_full):
        sw, _cond = self._setup_switch(fake_browser_full, True)
        sw._render()

        assert len(sw._children) == 1
        assert sw._children[0]._mounted is True


class TestComponentPatchingDecision:
    def test_is_patchable_allows_same_tag_components(self, fake_browser_full):
        from webcompy.components._component import HeadPropsStore
        from webcompy.components._generator import ComponentStore, define_component
        from webcompy.di import _pending_di_parent
        from webcompy.di._keys import _COMPONENT_STORE_KEY, _HEAD_PROPS_KEY
        from webcompy.di._scope import DIScope, _active_di_scope
        from webcompy.elements import html

        @define_component
        def CmpA(context):
            return html.DIV({}, "a")

        @define_component
        def CmpB(context):
            return html.DIV({}, "b")

        store = ComponentStore()
        head_props = HeadPropsStore()
        scope = DIScope()
        scope.provide(_COMPONENT_STORE_KEY, store)
        scope.provide(_HEAD_PROPS_KEY, head_props)
        di_token = _active_di_scope.set(scope)
        pending_token = _pending_di_parent.set(scope)
        try:
            c1 = CmpA(None)
            c2 = CmpB(None)
            assert _is_patchable(c1, c2) is True
        finally:
            _active_di_scope.reset(di_token)
            _pending_di_parent.reset(pending_token)
            scope.dispose()

    def test_is_patchable_rejects_different_tag_components(self, fake_browser_full):
        from webcompy.components._component import HeadPropsStore
        from webcompy.components._generator import ComponentStore, define_component
        from webcompy.di import _pending_di_parent
        from webcompy.di._keys import _COMPONENT_STORE_KEY, _HEAD_PROPS_KEY
        from webcompy.di._scope import DIScope, _active_di_scope
        from webcompy.elements import html

        @define_component
        def CmpDiv(context):
            return html.DIV({}, "div")

        @define_component
        def CmpSpan(context):
            return html.SPAN({}, "span")

        store = ComponentStore()
        head_props = HeadPropsStore()
        scope = DIScope()
        scope.provide(_COMPONENT_STORE_KEY, store)
        scope.provide(_HEAD_PROPS_KEY, head_props)
        di_token = _active_di_scope.set(scope)
        pending_token = _pending_di_parent.set(scope)
        try:
            c_div = CmpDiv(None)
            c_span = CmpSpan(None)
            assert _is_patchable(c_div, c_span) is False
        finally:
            _active_di_scope.reset(di_token)
            _pending_di_parent.reset(pending_token)
            scope.dispose()
