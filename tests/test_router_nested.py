from __future__ import annotations

from unittest.mock import MagicMock

from tests.conftest import MockHistoryPort
from webcompy.components import ComponentGenerator
from webcompy.router._router import Router


def _mock_comp(name="C"):
    return MagicMock(spec=ComponentGenerator)


class TestFlattenNested:
    def test_nested_two_levels(self):
        pages = [
            {
                "path": "/docs",
                "component": _mock_comp("Layout"),
                "children": [{"path": "/guide", "component": _mock_comp("Guide")}],
            }
        ]
        r = Router(*pages, history=MockHistoryPort(mode="hash"), preload=False)
        assert len(r.__routes__) == 1
        assert r.__routes__[0][0] == "docs/guide"
        assert len(r.__chains__[0].chain) == 2
        assert [node.segment for node in r.__chains__[0].chain] == ["docs", "guide"]

    def test_index_child(self):
        pages = [
            {
                "path": "/docs",
                "component": _mock_comp("Layout"),
                "children": [{"path": "", "component": _mock_comp("Index")}],
            }
        ]
        r = Router(*pages, history=MockHistoryPort(mode="hash"), preload=False)
        assert len(r.__routes__) == 1
        assert r.__routes__[0][0] == "docs"
        assert len(r.__chains__[0].chain) == 2
        assert [node.segment for node in r.__chains__[0].chain] == ["docs", ""]

    def test_bare_parent_no_index_no_leaf(self):
        pages = [
            {
                "path": "/docs",
                "component": _mock_comp("Layout"),
                "children": [{"path": "/guide", "component": _mock_comp("Guide")}],
            }
        ]
        r = Router(*pages, history=MockHistoryPort(mode="hash"), preload=False)
        assert all(route[0] != "docs" for route in r.__routes__)

    def test_flat_route_single_level_chain(self):
        pages = [{"path": "/users/{id}", "component": _mock_comp()}]
        r = Router(*pages, history=MockHistoryPort(mode="hash"), preload=False)
        assert len(r.__routes__) == 1
        assert len(r.__chains__[0].chain) == 1
        assert r.__chains__[0].per_level_param_names == (["id"],)

    def test_deep_nesting(self):
        pages = [
            {
                "path": "/a",
                "component": _mock_comp(),
                "children": [
                    {
                        "path": "/b",
                        "component": _mock_comp(),
                        "children": [{"path": "/c", "component": _mock_comp()}],
                    }
                ],
            }
        ]
        r = Router(*pages, history=MockHistoryPort(mode="hash"), preload=False)
        assert r.__routes__[0][0] == "a/b/c"
        assert len(r.__chains__[0].chain) == 3

    def test_path_joining_normalizes_slashes(self):
        pages = [
            {
                "path": "docs/",
                "component": _mock_comp(),
                "children": [{"path": "/guide/", "component": _mock_comp()}],
            }
        ]
        r = Router(*pages, history=MockHistoryPort(mode="hash"), preload=False)
        assert r.__routes__[0][0] == "docs/guide"

    def test_routes_and_chains_parallel(self):
        pages = [
            {
                "path": "/docs",
                "component": _mock_comp(),
                "children": [
                    {"path": "", "component": _mock_comp()},
                    {"path": "/guide", "component": _mock_comp()},
                ],
            }
        ]
        r = Router(*pages, history=MockHistoryPort(mode="hash"), preload=False)
        assert len(r.__routes__) == len(r.__chains__) == 2
        assert r.__routes__[0][0] == r.__chains__[0].full_path == "docs"
        assert r.__routes__[1][0] == r.__chains__[1].full_path == "docs/guide"

    def test_full_param_names_concatenated(self):
        pages = [
            {
                "path": "/users/{uid}",
                "component": _mock_comp(),
                "children": [{"path": "/docs/{doc_id}", "component": _mock_comp()}],
            }
        ]
        r = Router(*pages, history=MockHistoryPort(mode="hash"), preload=False)
        _path, _matcher, param_names, _comp, _page = r.__routes__[0]
        assert param_names == ["uid", "doc_id"]

    def test_leaf_component_is_deepest(self):
        guide = _mock_comp("Guide")
        pages = [
            {
                "path": "/docs",
                "component": _mock_comp("Layout"),
                "children": [{"path": "/guide", "component": guide}],
            }
        ]
        r = Router(*pages, history=MockHistoryPort(mode="hash"), preload=False)
        assert r.__routes__[0][3] is guide
        assert r.__routes__[0][4]["path"] == "/guide"

    def test_multiple_root_pages(self):
        pages = [
            {"path": "/home", "component": _mock_comp()},
            {
                "path": "/docs",
                "component": _mock_comp(),
                "children": [{"path": "/guide", "component": _mock_comp()}],
            },
        ]
        r = Router(*pages, history=MockHistoryPort(mode="hash"), preload=False)
        assert [route[0] for route in r.__routes__] == ["home", "docs/guide"]


class TestCloneForRequest:
    def test_clone_preserves_page_tree(self):
        pages = [
            {
                "path": "/docs",
                "component": _mock_comp(),
                "children": [{"path": "/guide", "component": _mock_comp()}],
            }
        ]
        r = Router(*pages, history=MockHistoryPort(mode="hash"), preload=False)
        cloned = r._clone_for_request()
        assert len(cloned.__routes__) == 1
        assert cloned.__routes__[0][0] == "docs/guide"
        assert len(cloned.__chains__[0].chain) == 2
        assert cloned is not r

    def test_clone_preserves_default_mode_base_url(self):
        default_gen = _mock_comp("Default")
        pages = [{"path": "/", "component": _mock_comp()}]
        r = Router(
            *pages,
            default=default_gen,
            history=MockHistoryPort(mode="history"),
            base_url="/app/",
            preload=False,
        )
        cloned = r._clone_for_request()
        assert cloned._default is default_gen
        assert cloned.__mode__ == "history"
        assert cloned.__base_url__ == "app"
        assert cloned._preload is False


class TestChainMatching:
    def test_match_nested_with_params(self):
        pages = [
            {
                "path": "/users/{uid}",
                "component": _mock_comp(),
                "children": [{"path": "/docs/{doc_id}", "component": _mock_comp()}],
            }
        ]
        r = Router(*pages, history=MockHistoryPort(mode="hash"), preload=False)
        r._history.navigate("/users/42/docs/7", None)
        match = r.current_match.value
        assert match is not None
        assert match.path_params == {"uid": "42", "doc_id": "7"}
        assert match.per_level_params == ({"uid": "42"}, {"doc_id": "7"})

    def test_no_match_returns_none(self):
        r = Router(history=MockHistoryPort(mode="hash"), preload=False)
        r._history.navigate("/nonexistent", None)
        assert r.current_match.value is None

    def test_index_match_chain(self):
        pages = [
            {
                "path": "/docs",
                "component": _mock_comp(),
                "children": [{"path": "", "component": _mock_comp("Index")}],
            }
        ]
        r = Router(*pages, history=MockHistoryPort(mode="hash"), preload=False)
        r._history.navigate("/docs", None)
        match = r.current_match.value
        assert match is not None
        assert len(match.chain) == 2
        assert match.chain[1].segment == ""

    def test_overlapping_sibling_patterns_first_wins(self):
        pages = [
            {
                "path": "/docs",
                "component": _mock_comp(),
                "children": [
                    {"path": "/new", "component": _mock_comp("New")},
                    {"path": "/{name}", "component": _mock_comp("Named")},
                ],
            }
        ]
        r = Router(*pages, history=MockHistoryPort(mode="hash"), preload=False)
        r._history.navigate("/docs/new", None)
        match = r.current_match.value
        assert match is not None
        assert match.chain[1].segment == "new"
        assert match.path_params == {}

        r._history.navigate("/docs/other", None)
        match = r.current_match.value
        assert match is not None
        assert match.chain[1].segment == "{name}"
        assert match.path_params == {"name": "other"}

    def test_index_vs_param_collision_definition_order(self):
        pages = [
            {
                "path": "/docs",
                "component": _mock_comp(),
                "children": [
                    {"path": "", "component": _mock_comp("Index")},
                    {"path": "/{name}", "component": _mock_comp("Named")},
                ],
            }
        ]
        r = Router(*pages, history=MockHistoryPort(mode="hash"), preload=False)
        r._history.navigate("/docs", None)
        match = r.current_match.value
        assert match is not None
        assert match.chain[1].segment == ""
        assert match.path_params == {}

        r._history.navigate("/docs/some-page", None)
        match = r.current_match.value
        assert match is not None
        assert match.chain[1].segment == "{name}"
        assert match.path_params == {"name": "some-page"}

    def test_duplicate_full_path_first_definition_wins(self):
        pages = [
            {
                "path": "/docs",
                "component": _mock_comp(),
                "children": [
                    {"path": "", "component": _mock_comp("FirstIndex")},
                    {"path": "/", "component": _mock_comp("SecondIndex")},
                ],
            }
        ]
        r = Router(*pages, history=MockHistoryPort(mode="hash"), preload=False)
        r._history.navigate("/docs", None)
        match = r.current_match.value
        assert match is not None
        assert match.chain[1].component == pages[0]["children"][0]["component"]

    def test_query_parsing(self):
        r = Router(
            {"path": "/", "component": _mock_comp()},
            history=MockHistoryPort(mode="hash"),
            preload=False,
        )
        r._history.navigate("/?tab=a&filter=active", None)
        match = r.current_match.value
        assert match is not None
        assert match.query == {"tab": "a", "filter": "active"}

    def test_query_empty(self):
        r = Router(
            {"path": "/", "component": _mock_comp()},
            history=MockHistoryPort(mode="hash"),
            preload=False,
        )
        r._history.navigate("/", None)
        match = r.current_match.value
        assert match is not None
        assert match.query == {}

    def test_history_mode_with_base_url(self):
        pages = [
            {
                "path": "/docs",
                "component": _mock_comp(),
                "children": [{"path": "/guide", "component": _mock_comp()}],
            }
        ]
        r = Router(
            *pages,
            history=MockHistoryPort(mode="history"),
            base_url="app",
            preload=False,
        )
        r._history.navigate("/app/docs/guide", None)
        match = r.current_match.value
        assert match is not None
        assert match.path == "/docs/guide"
        assert len(match.chain) == 2

    def test_state_captured(self):
        r = Router(
            {"path": "/", "component": _mock_comp()},
            history=MockHistoryPort(mode="hash"),
            preload=False,
        )
        r._history.navigate("/", {"k": "v"})
        match = r.current_match.value
        assert match is not None
        assert match.state == {"k": "v"}

    def test_flat_route_single_level_match(self):
        r = Router(
            {"path": "/users/{id}", "component": _mock_comp()},
            history=MockHistoryPort(mode="hash"),
            preload=False,
        )
        r._history.navigate("/users/42", None)
        match = r.current_match.value
        assert match is not None
        assert len(match.chain) == 1
        assert match.path_params == {"id": "42"}
        assert match.per_level_params == ({"id": "42"},)
