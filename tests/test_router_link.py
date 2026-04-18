from unittest.mock import MagicMock

from tests.conftest import FakeDOMEvent
from webcompy.elements.types._element import Element
from webcompy.router._link import TypedRouterLink
from webcompy.router._pages import RouterPage, WebComPyRouterException
from webcompy.router._router import Router
from webcompy.signal import Signal


class FakeRootElement(Element):
    _get_belonging_component = lambda self: ""
    _get_belonging_components = lambda self: ()


def _make_router(mode="hash", base_url=""):
    page = RouterPage(path="/home", component=MagicMock(spec=object))
    return Router(page, mode=mode, base_url=base_url)


class TestRouterLinkHref:
    def test_href_simple_path_hash(self):
        r = _make_router(mode="hash")
        TypedRouterLink.__set_router__(r)
        link = TypedRouterLink(to="/home", text=["Home"])
        href = link._href.value
        assert href.startswith("#")
        assert "home" in href

    def test_href_simple_path_history(self):
        r = _make_router(mode="history")
        TypedRouterLink.__set_router__(r)
        link = TypedRouterLink(to="/home", text=["Home"])
        href = link._href.value
        assert "home" in href
        assert not href.startswith("#")

    def test_href_with_base_url(self):
        r = _make_router(mode="history", base_url="app")
        TypedRouterLink.__set_router__(r)
        link = TypedRouterLink(to="/home", text=["Home"])
        href = link._href.value
        assert "app" in href

    def test_href_with_reactive_to(self):
        r = _make_router(mode="hash")
        TypedRouterLink.__set_router__(r)
        to = Signal("/home")
        link = TypedRouterLink(to=to, text=["Home"])
        href = link._href.value
        assert "home" in href

    def test_href_with_query(self):
        r = _make_router(mode="hash")
        TypedRouterLink.__set_router__(r)
        query = Signal({"q": "test"})
        link = TypedRouterLink(to="/search", text=["Search"], query=query)
        href = link._href.value
        assert "?" in href
        assert "q=test" in href

    def test_href_with_path_params(self):
        r = _make_router(mode="hash")
        TypedRouterLink.__set_router__(r)
        path_params = Signal({"id": "42"})
        link = TypedRouterLink(to="/users/{id}", text=["User"], path_params=path_params)
        href = link._href.value
        assert "42" in href


class TestRouterLinkGenerateAttrs:
    def test_generate_attrs_includes_href(self):
        r = _make_router(mode="hash")
        TypedRouterLink.__set_router__(r)
        link = TypedRouterLink(to="/home", text=["Home"])
        attrs = link._generate_attrs()
        assert "href" in attrs
        assert "webcompy-routerlink" in attrs

    def test_generate_attrs_with_custom_attrs(self):
        r = _make_router(mode="hash")
        TypedRouterLink.__set_router__(r)
        link = TypedRouterLink(to="/home", text=["Home"], attrs={"class": "nav-link"})
        attrs = link._generate_attrs()
        assert attrs["class"] == "nav-link"
        assert attrs["webcompy-routerlink"] is True


class TestRouterLinkInit:
    def test_init_raises_without_router(self):
        TypedRouterLink._router = None
        try:
            TypedRouterLink(to="/home", text=["Home"])
            raise AssertionError("Should have raised")
        except WebComPyRouterException:
            pass


class TestRouterLinkOnClickValidation:
    def test_on_click_raises_invalid_query_not_dict(self):
        r = _make_router(mode="hash")
        TypedRouterLink.__set_router__(r)
        link = TypedRouterLink(to="/home", text=["Home"])
        link._query = Signal("not-a-dict")
        ev = FakeDOMEvent(href="/home")
        try:
            link._on_click(ev)
            raise AssertionError("Should have raised")
        except (WebComPyRouterException, TypeError):
            pass

    def test_on_click_raises_invalid_params_not_dict(self):
        r = _make_router(mode="hash")
        TypedRouterLink.__set_router__(r)
        link = TypedRouterLink(to="/home", text=["Home"])
        link._params = Signal("not-a-dict")
        ev = FakeDOMEvent(href="/home")
        try:
            link._on_click(ev)
            raise AssertionError("Should have raised")
        except WebComPyRouterException:
            pass

    def test_on_click_no_browser_returns_early(self):
        r = _make_router(mode="hash")
        TypedRouterLink.__set_router__(r)
        link = TypedRouterLink(to="/home", text=["Home"])
        ev = FakeDOMEvent(href="/home")
        link._on_click(ev)
        ev.preventDefault.assert_called_once()
