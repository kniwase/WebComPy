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
