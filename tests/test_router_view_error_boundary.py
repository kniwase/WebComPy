from __future__ import annotations

from tests.conftest import MockHistoryPort
from webcompy.components import ComponentContext, define_component
from webcompy.di import DIScope
from webcompy.di._keys import _ROUTER_KEY
from webcompy.elements import ErrorBoundary, html
from webcompy.router import Router, RouterContext, RouterView
from webcompy_testing import TestRenderer

_crash = {"leaf": True, "default": True}


@define_component
def RootLayout(context: ComponentContext[None]):
    return html.DIV({"data-testid": "root"}, RouterView())


@define_component
def DocsLayout(context: ComponentContext[RouterContext]):
    return html.DIV(
        {"data-testid": "docs-layout"},
        html.SPAN({"data-testid": "layout-marker"}, "layout"),
        RouterView(),
    )


@define_component
def CrashingPage(context: ComponentContext[RouterContext]):
    if _crash["leaf"]:
        raise RuntimeError("leaf crash")
    return html.DIV({"data-testid": "crashing-page"}, "leaf ok")


@define_component
def GuidePage(context: ComponentContext[RouterContext]):
    return html.DIV({"data-testid": "guide-page"}, "guide")


@define_component
def CrashingChild(context: ComponentContext[None]):
    raise RuntimeError("inner crash")


@define_component
def PageWithInnerBoundary(context: ComponentContext[RouterContext]):
    return html.DIV(
        {"data-testid": "inner-page"},
        ErrorBoundary(
            children=lambda: CrashingChild(None),
            fallback=lambda e, r: html.DIV({"data-testid": "inner-fallback"}, "inner fb"),
        ),
    )


@define_component
def CrashingDefault(context: ComponentContext[RouterContext]):
    if _crash["default"]:
        raise RuntimeError("default crash")
    return html.DIV({"data-testid": "default-page"}, "default ok")


def _make_router() -> tuple[Router, MockHistoryPort]:
    _crash["leaf"] = True
    _crash["default"] = True
    hist = MockHistoryPort(mode="hash")
    router = Router(
        {
            "path": "/docs",
            "component": DocsLayout,
            "children": [
                {"path": "/crash", "component": CrashingPage},
                {"path": "/guide", "component": GuidePage},
                {"path": "/inner", "component": PageWithInnerBoundary},
            ],
        },
        default=CrashingDefault,
        history=hist,
        preload=False,
    )
    return router, hist


def _render(router: Router):
    scope = DIScope()
    scope.provide(_ROUTER_KEY, router)
    return TestRenderer.render(RootLayout, parent_scope=scope)


class TestImplicitBoundary:
    def test_page_crash_preserves_layout(self):
        router, hist = _make_router()
        hist.navigate("/docs/crash", None)
        with _render(router) as result:
            assert result.find_by_attribute("data-testid", "docs-layout") is not None
            assert result.find_by_attribute("data-testid", "layout-marker") is not None
            assert result.find_by_attribute("data-testid", "crashing-page") is None

    def test_renavigation_retries_errored_level(self):
        router, hist = _make_router()
        hist.navigate("/docs/crash", None)
        with _render(router) as result:
            assert result.find_by_attribute("data-testid", "crashing-page") is None

            _crash["leaf"] = False
            router.__set_path__("/docs/crash", None)

            assert result.find_by_attribute("data-testid", "crashing-page") is not None
            assert result.find_by_attribute("data-testid", "docs-layout") is not None

    def test_remount_drops_error_state(self):
        router, hist = _make_router()
        hist.navigate("/docs/crash", None)
        with _render(router) as result:
            assert result.find_by_attribute("data-testid", "crashing-page") is None

            _crash["leaf"] = False
            router.__set_path__("/docs/guide", None)
            assert result.find_by_attribute("data-testid", "guide-page") is not None

            router.__set_path__("/docs/crash", None)
            assert result.find_by_attribute("data-testid", "crashing-page") is not None

    def test_app_declared_inner_boundary_engages_first(self):
        router, hist = _make_router()
        hist.navigate("/docs/inner", None)
        with _render(router) as result:
            assert result.find_by_attribute("data-testid", "inner-page") is not None
            assert result.find_by_attribute("data-testid", "inner-fallback") is not None
            assert result.find_by_attribute("data-testid", "docs-layout") is not None

    def test_default_view_crash_is_isolated(self):
        router, hist = _make_router()
        hist.navigate("/nonexistent", None)
        with _render(router) as result:
            assert result.find_by_attribute("data-testid", "root") is not None
            assert result.find_by_attribute("data-testid", "default-page") is None
            assert result.find_by_attribute("data-testid", "docs-layout") is None

    def test_default_view_retry_on_renavigation(self):
        router, hist = _make_router()
        hist.navigate("/nonexistent", None)
        with _render(router) as result:
            assert result.find_by_attribute("data-testid", "default-page") is None

            _crash["default"] = False
            router.__set_path__("/nonexistent", None)

            assert result.find_by_attribute("data-testid", "default-page") is not None
