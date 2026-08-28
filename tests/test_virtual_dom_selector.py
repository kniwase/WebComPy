"""Unit tests for the server virtual DOM CSS selector engine."""

import pytest

from webcompy_server.ports._dom import ServerDOMPort
from webcompy_server.ports._selector import parse_selector, resolve_first


def build(port: ServerDOMPort, spec: dict) -> object:
    """Build a virtual tree from a nested ``{tag, attrs, children}`` spec."""
    node = port.create_element(spec["tag"])
    for name, value in spec.get("attrs", {}).items():
        node.setAttribute(name, value)
    for child in spec.get("children", []):
        if isinstance(child, str):
            node.appendChild(port.create_text_node(child))
        else:
            node.appendChild(build(port, child))
    return node


@pytest.fixture
def port() -> ServerDOMPort:
    return ServerDOMPort()


class TestParseSelector:
    @pytest.mark.parametrize(
        "selector",
        ["div", ".a", "#a", "div.a#b", "div .a", "div > .a", ".x, .y", "div.a #b.c", "#root ul > li.item"],
    )
    def test_supported_subset_parses(self, selector):
        assert len(parse_selector(selector)) >= 1

    def test_comma_groups_count(self):
        assert len(parse_selector(".a, .b ,.c")) == 3

    @pytest.mark.parametrize(
        "selector",
        ["input[type=text]", "div:hover", "*", "", "   ", ",,.a", ".a,", "> div", "div >", '.a["b"]'],
    )
    def test_unsupported_syntax_raises(self, selector):
        with pytest.raises(ValueError):
            parse_selector(selector)


class TestResolveFirst:
    def test_id_selector_resolves(self, port):
        root = build(port, {"tag": "body", "children": [{"tag": "div", "attrs": {"id": "footer-root"}}]})
        found = resolve_first(root, "#footer-root")
        assert found is not None
        assert found.getAttribute("id") == "footer-root"

    def test_class_selector_resolves_first_document_order(self, port):
        root = build(
            port,
            {
                "tag": "div",
                "attrs": {"class": "wrapper"},
                "children": [
                    {"tag": "section", "children": [{"tag": "span", "attrs": {"class": "menu-host"}}]},
                    {"tag": "aside", "attrs": {"class": "menu-host"}},
                ],
            },
        )
        found = resolve_first(root, ".menu-host")
        assert found is not None
        assert found.nodeName.lower() == "span"

    def test_descendant_combinator(self, port):
        root = build(
            port,
            {
                "tag": "div",
                "attrs": {"class": "wrapper"},
                "children": [{"tag": "ul", "children": [{"tag": "li", "attrs": {"class": "item"}}]}],
            },
        )
        assert resolve_first(root, ".wrapper .item") is not None
        assert resolve_first(root, ".missing .item") is None

    def test_child_combinator_restricts_parentage(self, port):
        root = build(
            port,
            {
                "tag": "div",
                "attrs": {"class": "a"},
                "children": [
                    {"tag": "section", "children": [{"tag": "p", "attrs": {"class": "b"}}]},
                    {"tag": "p", "attrs": {"class": "b"}},
                ],
            },
        )
        found = resolve_first(root, ".a > .b")
        assert found is not None
        assert found.nodeName.lower() == "p"
        assert found.parentNode.nodeName.lower() == "div"

    def test_compound_selector_requires_all_terms(self, port):
        root = build(
            port,
            {
                "tag": "div",
                "children": [
                    {"tag": "div", "attrs": {"id": "only-id"}},
                    {"tag": "div", "attrs": {"id": "both", "class": "cls"}},
                ],
            },
        )
        found = resolve_first(root, "div.cls#both")
        assert found is not None
        assert found.getAttribute("id") == "both"

    def test_comma_group_returns_earliest_match_in_tree_order(self, port):
        root = build(
            port,
            {
                "tag": "div",
                "children": [
                    {"tag": "section", "children": [{"tag": "em", "attrs": {"class": "y"}}]},
                    {"tag": "strong", "attrs": {"class": "x"}},
                ],
            },
        )
        found = resolve_first(root, ".x, .y")
        assert found is not None
        assert found.getAttribute("class") == "y"

    def test_root_itself_can_match(self, port):
        root = build(port, {"tag": "body"})
        assert resolve_first(root, "body") is root

    def test_no_match_returns_none(self, port):
        root = build(port, {"tag": "body", "children": [{"tag": "p"}]})
        assert resolve_first(root, ".nothing") is None

    def test_comment_and_text_nodes_never_match_or_block(self, port):
        root = build(port, {"tag": "div", "children": [{"tag": "span"}]})
        comment = port.create_comment("webcompy-teleport-anchor")
        comment_after = port.create_comment("wc-teleport-block:0:%23target")
        children = root.childNodes
        first = children[0]
        root.insertBefore(comment, first)
        root.appendChild(comment_after)
        assert resolve_first(root, "span") is not None
        assert resolve_first(root, "#comment") is None

    def test_query_is_read_only(self, port):
        spec = {
            "tag": "body",
            "attrs": {"id": "doc-body"},
            "children": [{"tag": "div", "attrs": {"class": "c1"}}],
        }
        root = build(port, spec)
        before = port.render_html(root)
        resolve_first(root, "#doc-body .c1")
        resolve_first(root, "div, body")
        after = port.render_html(root)
        assert before == after

    def test_multiple_spaces_normalise_to_single_combinator(self, port):
        root = build(
            port,
            {
                "tag": "main",
                "children": [{"tag": "nav", "children": [{"tag": "a"}]}],
            },
        )
        assert resolve_first(root, "main     nav      a") is not None


class TestCaseSensitivity:
    def test_class_selector_matches_case_sensitively(self, port):
        root = build(
            port,
            {
                "tag": "div",
                "children": [{"tag": "span", "attrs": {"class": "Foo"}}],
            },
        )
        found = resolve_first(root, ".Foo")
        assert found is not None
        assert found.getAttribute("class") == "Foo"
        assert resolve_first(root, ".foo") is None

    def test_class_selector_case_insensitive_match_does_not_leak(self, port):
        root = build(
            port,
            {
                "tag": "div",
                "children": [
                    {"tag": "span", "attrs": {"class": "menu-Host"}},
                    {"tag": "em", "attrs": {"class": "menu-host"}},
                ],
            },
        )
        found = resolve_first(root, ".menu-host")
        assert found is not None
        assert found.nodeName.lower() == "em"

    def test_compound_class_and_id_match_case_sensitively(self, port):
        root = build(
            port,
            {
                "tag": "div",
                "children": [{"tag": "span", "attrs": {"id": "Bar", "class": "Foo"}}],
            },
        )
        assert resolve_first(root, "span.Foo#Bar") is not None
        assert resolve_first(root, "span.foo#Bar") is None
        assert resolve_first(root, "span.Foo#bar") is None

    def test_tag_selector_matches_case_insensitively(self, port):
        root = build(
            port,
            {
                "tag": "div",
                "children": [{"tag": "section", "attrs": {"class": "Panel"}}],
            },
        )
        found = resolve_first(root, "SECTION.Panel")
        assert found is not None
        assert found.nodeName.lower() == "section"
