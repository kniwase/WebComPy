from tests.conftest import FakeDOMNode
from webcompy.elements.types._element import Element
from webcompy.elements.types._text import TextElement
from webcompy.reactive import Reactive


class FakeRootElement(Element):
    _get_belonging_component = lambda self: ""
    _get_belonging_components = lambda self: ()


def _make_parent():
    parent = FakeRootElement("div", {}, {}, None, None)
    parent._node_cache = FakeDOMNode("div")
    parent._mounted = True
    return parent


class TestCreateChildElement:
    def test_none_child_returns_none(self):
        parent = _make_parent()
        el = FakeRootElement("div", {}, {}, None, None)
        result = el._create_child_element(parent, 0, None)
        assert result is None

    def test_string_child_creates_text_element(self):
        parent = _make_parent()
        el = FakeRootElement("div", {}, {}, None, None)
        result = el._create_child_element(parent, 0, "hello")
        assert isinstance(result, TextElement)
        assert result._text == "hello"

    def test_reactive_child_creates_text_element(self):
        parent = _make_parent()
        el = FakeRootElement("div", {}, {}, None, None)
        r = Reactive("world")
        result = el._create_child_element(parent, 0, r)
        assert isinstance(result, TextElement)

    def test_element_child_passes_through(self):
        parent = _make_parent()
        el = FakeRootElement("div", {}, {}, None, None)
        child = FakeRootElement("span", {}, {}, None, None)
        result = el._create_child_element(parent, 0, child)
        assert result is child

    def test_sets_node_idx_and_parent(self):
        parent = _make_parent()
        el = FakeRootElement("div", {}, {}, None, None)
        result = el._create_child_element(parent, 5, "hello")
        assert result._node_idx == 5
        assert result._parent is parent


class TestReIndexChildren:
    def test_re_index_children(self):
        parent = _make_parent()
        parent._append_child("a")
        parent._append_child("b")
        parent._append_child("c")
        parent._re_index_children(False)
        assert parent._children[0]._node_idx == 0
        assert parent._children[1]._node_idx == 1
        assert parent._children[2]._node_idx == 2


class TestInsertChild:
    def test_insert_child_at_index(self):
        parent = _make_parent()
        parent._append_child("first")
        parent._append_child("third")
        parent._insert_child(1, "second")
        assert len(parent._children) == 3
        texts = [c._get_text() for c in parent._children if hasattr(c, "_get_text")]
        assert "second" in texts


class TestPopChild:
    def test_pop_child_removes_at_index(self, monkeypatch):
        import importlib

        from tests.conftest import FakeBrowserModule

        fake = FakeBrowserModule()
        for mod_name in [
            "webcompy.elements.types._element",
            "webcompy.elements.types._abstract",
            "webcompy.elements.types._text",
        ]:
            mod = importlib.import_module(mod_name)
            monkeypatch.setattr(mod, "browser", fake)
        parent = _make_parent()
        parent._append_child("a")
        parent._append_child("b")
        parent._append_child("c")
        parent._children[1]._node_cache = FakeDOMNode("span")
        parent._children[1]._mounted = True
        parent._pop_child(1, re_index=False)
        assert len(parent._children) == 2


class TestRenderHtml:
    def test_render_html_with_attrs(self):
        parent = _make_parent()
        parent._append_child("hello")
        html = parent._render_html()
        assert "div" in html
        assert "hello" in html

    def test_render_html_newline_indented(self):
        parent = _make_parent()
        parent._append_child("child")
        html = parent._render_html(newline=True, indent=2)
        assert "\n" in html
