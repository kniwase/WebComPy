from tests.conftest import FakeDOMNode
from webcompy.elements.types._element import Element
from webcompy.elements.types._repeat import RepeatElement
from webcompy.elements.types._text import TextElement
from webcompy.reactive import ReactiveList


class FakeRootElement(Element):
    _get_belonging_component = lambda self: ""
    _get_belonging_components = lambda self: ()


def _make_parent():
    parent = FakeRootElement("div", {}, {}, None, None)
    parent._node_cache = FakeDOMNode("div")
    parent._mounted = True
    return parent


class TestRepeatElementValidation:
    def test_non_reactive_sequence_raises(self):
        try:
            RepeatElement([1, 2, 3], lambda x: TextElement(str(x)))
            raise AssertionError("Should have raised ValueError")
        except ValueError as e:
            assert "Reactive" in str(e)


class TestRepeatElementOnSetParent:
    def test_on_set_parent_generates_children(self):
        rl = ReactiveList(["a", "b", "c"])
        rep = RepeatElement(rl, lambda x: TextElement(x))
        parent = _make_parent()
        rep._parent = parent
        rep._node_idx = 0
        rep._on_set_parent()
        assert len(rep._children) == 3

    def test_on_set_parent_empty_list(self):
        rl = ReactiveList([])
        rep = RepeatElement(rl, lambda x: TextElement(x))
        parent = _make_parent()
        rep._parent = parent
        rep._node_idx = 0
        rep._on_set_parent()
        assert len(rep._children) == 0


class TestRepeatElementKeySupport:
    def test_keyed_on_set_parent_populates_key_map(self):
        rl = ReactiveList(["a", "b", "c"])
        rep = RepeatElement(rl, lambda x: TextElement(x), key=lambda x: x)
        parent = _make_parent()
        rep._parent = parent
        rep._node_idx = 0
        rep._on_set_parent()
        assert rep._children_keys == ["a", "b", "c"]
        assert "a" in rep._key_to_child

    def test_keyed_empty_list(self):
        rl = ReactiveList([])
        rep = RepeatElement(rl, lambda x: TextElement(x), key=lambda x: x)
        parent = _make_parent()
        rep._parent = parent
        rep._node_idx = 0
        rep._on_set_parent()
        assert rep._children_keys == []

    def test_key_defaults_to_none(self):
        rl = ReactiveList(["a"])
        rep = RepeatElement(rl, lambda x: TextElement(x))
        assert rep._key is None


class TestMultiLineTextElement:
    def test_multiline_text_splits_lines(self):
        from webcompy.elements.types._repeat import MultiLineTextElement

        parent = _make_parent()
        mlt = MultiLineTextElement("hello\nworld")
        mlt._parent = parent
        mlt._node_idx = 0
        mlt._on_set_parent()
        assert len(mlt._children) == 3
