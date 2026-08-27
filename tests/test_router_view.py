from __future__ import annotations

from tests.conftest import MockHistoryPort
from webcompy.components import ComponentContext, define_component
from webcompy.di import DIScope
from webcompy.di._keys import _ROUTER_KEY
from webcompy.elements import html
from webcompy.router import Router, RouterContext, RouterView
from webcompy_testing import TestRenderer

_setup_counts: dict[str, list[int]] = {}


def _count(name: str) -> int:
    counts = _setup_counts.setdefault(name, [0])
    counts[0] += 1
    return counts[0]


def _reset_counts() -> None:
    _setup_counts.clear()


@define_component()
def RootLayout(context: ComponentContext[None]):
    return html.DIV({"data-testid": "root"}, RouterView())


@define_component()
def DocsLayout(context: ComponentContext[RouterContext]):
    _count("DocsLayout")
    return html.DIV(
        {"data-testid": "docs-layout"},
        html.SPAN({"data-testid": "docs-layout-count"}, str(_setup_counts["DocsLayout"][0])),
        RouterView(),
    )


@define_component()
def GuidePage(context: ComponentContext[RouterContext]):
    _count("GuidePage")
    return html.DIV({"data-testid": "guide-page"}, f"guide-{_setup_counts['GuidePage'][0]}")


@define_component()
def ApiPage(context: ComponentContext[RouterContext]):
    _count("ApiPage")
    return html.DIV({"data-testid": "api-page"}, f"api-{_setup_counts['ApiPage'][0]}")


@define_component()
def ParamPage(context: ComponentContext[RouterContext]):
    _count("ParamPage")
    return html.DIV(
        {"data-testid": "param-page"},
        html.SPAN({"data-testid": "param-name"}, str(context.props.path_params.get("name"))),
        html.SPAN({"data-testid": "param-count"}, str(_setup_counts["ParamPage"][0])),
    )


@define_component()
def DeepNestedPage(context: ComponentContext[RouterContext]):
    _count("DeepNestedPage")
    return html.DIV({"data-testid": "deep-nested-page"}, "deep")


@define_component()
def NotFoundPage(context: ComponentContext[RouterContext]):
    _count("NotFoundPage")
    return html.DIV({"data-testid": "not-found-page"}, "default")


@define_component()
def DeepLayout(context: ComponentContext[RouterContext]):
    _count("DeepLayout")
    return html.DIV(
        {"data-testid": "deep-layout"},
        RouterView(),
        RouterView(),
    )


@define_component()
def LevelOneLeaf(context: ComponentContext[RouterContext]):
    _count("LevelOneLeaf")
    return html.DIV(
        {"data-testid": "leaf-page"},
        html.DIV({"data-testid": "deep-slot"}, RouterView()),
    )


def _make_router(*, mode: str = "hash") -> tuple[Router, MockHistoryPort]:
    _reset_counts()
    hist = MockHistoryPort(mode=mode)
    router = Router(
        {
            "path": "/docs",
            "component": DocsLayout,
            "children": [
                {"path": "/guide", "component": GuidePage},
                {"path": "/api", "component": ApiPage},
                {"path": "/{name}", "component": ParamPage},
                {
                    "path": "/deep",
                    "component": DeepLayout,
                    "children": [{"path": "/x", "component": DeepNestedPage}],
                },
            ],
        },
        history=hist,
        preload=False,
    )
    return router, hist


def _render(router: Router) -> TestRenderer:
    scope = DIScope()
    scope.provide(_ROUTER_KEY, router)
    return TestRenderer.render(RootLayout, parent_scope=scope)


class TestRouterViewLevelRendering:
    def test_root_view_renders_layout_and_nested_view_renders_leaf(self):
        router, hist = _make_router()
        hist.navigate("/docs/guide", None)
        with _render(router) as result:
            assert result.find_by_attribute("data-testid", "docs-layout") is not None
            assert result.find_by_attribute("data-testid", "guide-page") is not None
            assert result.find_by_attribute("data-testid", "api-page") is None

    def test_view_deeper_than_chain_renders_empty(self):
        router, hist = _make_router()
        hist.navigate("/docs/deep/x", None)
        with _render(router) as result:
            assert result.find_by_attribute("data-testid", "deep-layout") is not None
            assert result.find_by_attribute("data-testid", "deep-nested-page") is not None

        hist.navigate("/docs/guide", None)
        with _render(router) as result:
            assert result.find_by_attribute("data-testid", "docs-layout") is not None
            assert result.find_by_attribute("data-testid", "guide-page") is not None

    def test_mounted_view_deeper_than_chain_renders_empty(self):
        hist = MockHistoryPort(mode="hash")
        router = Router(
            {
                "path": "/docs",
                "component": DocsLayout,
                "children": [{"path": "/guide", "component": LevelOneLeaf}],
            },
            history=hist,
            preload=False,
        )
        _reset_counts()
        hist.navigate("/docs/guide", None)
        with _render(router) as result:
            assert result.find_by_attribute("data-testid", "leaf-page") is not None
            deep_slot = result.find_by_attribute("data-testid", "deep-slot")
            assert deep_slot is not None
            assert deep_slot.childNodes.length == 0, "depth-2 view must render empty when the chain has 2 levels"
            assert _setup_counts["LevelOneLeaf"][0] == 1

    def test_no_match_renders_empty_view(self):
        router, hist = _make_router()
        hist.navigate("/nonexistent", None)
        with _render(router) as result:
            assert result.find_by_attribute("data-testid", "root") is not None
            assert result.find_by_attribute("data-testid", "docs-layout") is None

    def test_no_match_with_default_renders_default(self):
        hist = MockHistoryPort(mode="hash")
        router = Router(
            {"path": "/docs", "component": DocsLayout},
            default=NotFoundPage,
            history=hist,
            preload=False,
        )
        _reset_counts()
        hist.navigate("/nonexistent", None)
        with _render(router) as result:
            assert result.find_by_attribute("data-testid", "not-found-page") is not None
            assert _setup_counts["NotFoundPage"][0] == 1

            router.__set_path__("/docs", None)

            assert result.find_by_attribute("data-testid", "docs-layout") is not None
            assert result.find_by_attribute("data-testid", "not-found-page") is None

            router.__set_path__("/another-missing", None)

            assert result.find_by_attribute("data-testid", "not-found-page") is not None
            assert _setup_counts["NotFoundPage"][0] == 2, "default must remount on path change"

    def test_no_match_without_default_shows_not_found_text(self):
        router, hist = _make_router()
        hist.navigate("/nonexistent", None)
        with _render(router) as result:
            assert result.find_by_text("Not Found") is not None


class TestRouterViewReuse:
    def test_sibling_navigation_preserves_parent_instance(self):
        router, hist = _make_router()
        hist.navigate("/docs/guide", None)
        with _render(router) as result:
            assert result.find_by_attribute("data-testid", "guide-page") is not None
            assert _setup_counts["DocsLayout"][0] == 1
            assert _setup_counts["GuidePage"][0] == 1

            router.__set_path__("/docs/api", None)

            assert result.find_by_attribute("data-testid", "api-page") is not None
            assert result.find_by_attribute("data-testid", "guide-page") is None
            assert _setup_counts["DocsLayout"][0] == 1, "layout setup must NOT re-run"
            assert _setup_counts["ApiPage"][0] == 1
            assert _setup_counts["GuidePage"][0] == 1

    def test_deeper_view_reacts_when_ancestor_preserved(self):
        router, hist = _make_router()
        hist.navigate("/docs/guide", None)
        with _render(router) as result:
            assert result.find_by_attribute("data-testid", "guide-page") is not None
            assert _setup_counts["GuidePage"][0] == 1

            router.__set_path__("/docs/api", None)

            # The remount guard must NOT over-skip: with all ancestors preserved,
            # the depth-1 view reacts on its own and remounts the leaf once.
            assert _setup_counts["DocsLayout"][0] == 1, "layout must be preserved"
            assert _setup_counts["ApiPage"][0] == 1, "leaf must be created exactly once"
            assert result.find_by_attribute("data-testid", "api-page") is not None
            assert result.find_by_attribute("data-testid", "guide-page") is None

    def test_param_change_remounts_leaf_only(self):
        router, hist = _make_router()
        hist.navigate("/docs/foo", None)
        with _render(router) as result:
            assert result.find_by_attribute("data-testid", "param-page") is not None
            assert _setup_counts["DocsLayout"][0] == 1
            assert _setup_counts["ParamPage"][0] == 1
            param_name = result.find_by_attribute("data-testid", "param-name")
            assert param_name is not None
            assert param_name.textContent == "foo"

            router.__set_path__("/docs/bar", None)

            assert _setup_counts["DocsLayout"][0] == 1, "layout setup must NOT re-run"
            assert _setup_counts["ParamPage"][0] == 2, "leaf must remount on param change"
            param_name = result.find_by_attribute("data-testid", "param-name")
            assert param_name is not None
            assert param_name.textContent == "bar"

    def test_query_change_remounts_level(self):
        router, hist = _make_router()
        hist.navigate("/docs/guide", None)
        with _render(router) as result:
            assert result.find_by_attribute("data-testid", "guide-page") is not None
            assert _setup_counts["GuidePage"][0] == 1

            router.__set_path__("/docs/guide?tab=b", None)

            # query is part of every level identity -> layout remounts too.
            # the depth-1 view defers to the remounting layout (no transient
            # leaf creation), so the leaf is created exactly once by the fresh
            # nested view inside the new layout.
            assert _setup_counts["DocsLayout"][0] == 2, "layout must remount (query is part of level identity)"
            assert _setup_counts["GuidePage"][0] == 2, "leaf must be created once (no transient creation)"
            assert result.find_by_attribute("data-testid", "guide-page") is not None

    def test_navigating_away_destroys_and_back_remounts(self):
        router, hist = _make_router()
        hist.navigate("/docs/guide", None)
        with _render(router) as result:
            assert result.find_by_attribute("data-testid", "guide-page") is not None
            assert _setup_counts["DocsLayout"][0] == 1

            router.__set_path__("/nonexistent", None)

            assert result.find_by_attribute("data-testid", "docs-layout") is None
            assert result.find_by_attribute("data-testid", "guide-page") is None

            router.__set_path__("/docs/guide", None)

            assert result.find_by_attribute("data-testid", "docs-layout") is not None
            assert result.find_by_attribute("data-testid", "guide-page") is not None
            assert _setup_counts["DocsLayout"][0] == 2, "layout must remount after no-match"

    def test_ancestor_param_change_remounts_descendants(self):
        router, hist = MockHistoryPort(mode="hash"), None
        _reset_counts()

        def _param_route_router() -> tuple[Router, MockHistoryPort]:
            hist = MockHistoryPort(mode="hash")
            router = Router(
                {
                    "path": "/users/{uid}",
                    "component": DocsLayout,
                    "children": [{"path": "/docs/{name}", "component": ParamPage}],
                },
                history=hist,
                preload=False,
            )
            return router, hist

        router, hist = _param_route_router()
        hist.navigate("/users/1/docs/a", None)
        with _render(router) as result:
            assert _setup_counts["DocsLayout"][0] == 1
            assert _setup_counts["ParamPage"][0] == 1
            param_name = result.find_by_attribute("data-testid", "param-name")
            assert param_name is not None
            assert param_name.textContent == "a"

            router.__set_path__("/users/2/docs/b", None)

            assert _setup_counts["DocsLayout"][0] == 2, "ancestor param change must remount layout"
            assert _setup_counts["ParamPage"][0] == 2, "descendant must be created once (no transient creation)"
            param_name = result.find_by_attribute("data-testid", "param-name")
            assert param_name is not None
            assert param_name.textContent == "b"


class TestRouterViewInFlightNavigation:
    def test_stale_route_render_callbacks_are_skipped(self):
        import asyncio

        from webcompy.components._component import _active_app_context
        from webcompy.components._hooks import on_after_rendering

        fired: list[str] = []

        @define_component()
        def HomePage(context: ComponentContext[RouterContext]):
            return html.DIV({"data-testid": "home-page"}, "home")

        @define_component()
        async def SlowPage(context: ComponentContext[RouterContext]):
            @on_after_rendering
            def after():
                fired.append("slow")

            await asyncio.sleep(0.02)
            return html.DIV({"data-testid": "slow-page"}, "slow")

        @define_component()
        async def FastPage(context: ComponentContext[RouterContext]):
            @on_after_rendering
            def after():
                fired.append("fast")

            await asyncio.sleep(0.001)
            return html.DIV({"data-testid": "fast-page"}, "fast")

        class _FakeDeferApp:
            def __init__(self):
                self._defer_depth = 0
                self._deferred_callbacks: list = []

        pages = [
            {"path": "/home", "component": HomePage},
            {"path": "/slow", "component": SlowPage},
            {"path": "/fast", "component": FastPage},
        ]
        hist = MockHistoryPort(mode="hash")
        router = Router(*pages, history=hist, preload=False)
        hist.navigate("/home", None)
        _reset_counts()
        with _render(router) as result:
            view = result._instance._children[0]._children[0]

            scratch = Router(*pages, history=MockHistoryPort(mode="hash"), preload=False)
            scratch._history.navigate("/slow", None)
            match_slow = scratch.current_match.value
            scratch._history.navigate("/fast", None)
            match_fast = scratch.current_match.value

            fake_app = _FakeDeferApp()
            token = _active_app_context.set(fake_app)
            try:
                from webcompy_testing._utils import run_sync

                async def _race():
                    await asyncio.gather(
                        view._on_match_changed(match_slow),
                        view._on_match_changed(match_fast),
                    )

                run_sync(_race())
            finally:
                _active_app_context.reset(token)

            assert fired == ["fast"], "stale render callbacks must not run after a newer navigation committed"
            assert view._mounted_component is not None
            assert fake_app._defer_depth == 0, "defer depth must be balanced after a stale render"
