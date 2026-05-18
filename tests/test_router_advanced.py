from unittest.mock import MagicMock

from tests.conftest import MockHistoryPort
from webcompy.components import ComponentGenerator
from webcompy.router._pages import RouterPage
from webcompy.router._router import Router


class TestRouterInit:
    def test_init_sets_mode(self):
        page = RouterPage(path="/", component=MagicMock(spec=ComponentGenerator))
        hist = MockHistoryPort(mode="hash")
        r = Router(page, history=hist)
        assert r.__mode__ == "hash"

    def test_init_strips_base_url(self):
        page = RouterPage(path="/", component=MagicMock(spec=ComponentGenerator))
        hist = MockHistoryPort(mode="history")
        r = Router(page, history=hist, base_url="/app/")
        assert r.__base_url__ == "app"


class TestRouterRouteGeneration:
    def test_generate_routes(self):
        page = RouterPage(path="/users", component=MagicMock(spec=ComponentGenerator))
        hist = MockHistoryPort(mode="hash")
        r = Router(page, history=hist)
        assert len(r.__routes__) == 1
        path_str, _matcher, _param_names, _component, _page_obj = r.__routes__[0]
        assert path_str == "users"

    def test_generate_routes_with_params(self):
        page = RouterPage(path="/users/{id}", component=MagicMock(spec=ComponentGenerator))
        hist = MockHistoryPort(mode="hash")
        r = Router(page, history=hist)
        _path_str, _matcher, param_names, _component, _page_obj = r.__routes__[0]
        assert "id" in param_names


class TestRouterGetCurrentPath:
    def test_get_current_path_no_query(self):
        page = RouterPage(path="/", component=MagicMock(spec=ComponentGenerator))
        hist = MockHistoryPort(mode="hash")
        r = Router(page, history=hist)
        r._history._value = "/home"
        pathname, search = r._get_current_path()
        assert pathname == "/home"
        assert search == ""

    def test_get_current_path_with_query(self):
        page = RouterPage(path="/", component=MagicMock(spec=ComponentGenerator))
        hist = MockHistoryPort(mode="hash")
        r = Router(page, history=hist)
        r._history._value = "/home?key=val&foo=bar"
        pathname, search = r._get_current_path()
        assert pathname == "/home"
        assert search == "key=val&foo=bar"


class TestRouterGenerateRouterContext:
    def test_context_with_query(self):
        page = RouterPage(path="/", component=MagicMock(spec=ComponentGenerator))
        hist = MockHistoryPort(mode="hash")
        r = Router(page, history=hist)
        ctx = r._generate_router_context("/search", "q=hello&page=1", None, [])
        assert ctx.query == {"q": "hello", "page": "1"}

    def test_context_empty_query(self):
        page = RouterPage(path="/", component=MagicMock(spec=ComponentGenerator))
        hist = MockHistoryPort(mode="hash")
        r = Router(page, history=hist)
        ctx = r._generate_router_context("/home", "", None, [])
        assert ctx.query == {}

    def test_context_with_path_params(self):
        page = RouterPage(path="/users/{id}", component=MagicMock(spec=ComponentGenerator))
        hist = MockHistoryPort(mode="hash")
        r = Router(page, history=hist)
        import re

        match = re.match(r"([^/]*?)$", "42")
        ctx = r._generate_router_context("/users/42", "", match, ["id"])
        assert ctx.path_params == {"id": "42"}

    def test_context_without_path_params(self):
        page = RouterPage(path="/", component=MagicMock(spec=ComponentGenerator))
        hist = MockHistoryPort(mode="hash")
        r = Router(page, history=hist)
        ctx = r._generate_router_context("/home", "", None, [])
        assert ctx.path_params == {}


class TestRouterSetPath:
    def test_set_path_delegates_to_history(self):
        page = RouterPage(path="/", component=MagicMock(spec=ComponentGenerator))
        hist = MockHistoryPort(mode="hash")
        r = Router(page, history=hist)
        r.__set_path__("/new/path", {"key": "val"})
        assert r._history._value == "/new/path"


class TestRouterDefault:
    def test_default_with_default_component(self):
        _mock_gen = MagicMock(spec=ComponentGenerator)
        page = RouterPage(path="/nonexistent", component=MagicMock(spec=ComponentGenerator))
        default_gen = MagicMock(spec=ComponentGenerator)
        hist = MockHistoryPort(mode="hash")
        r = Router(page, default=default_gen, history=hist)
        r._history._value = "/not-a-route"
        r.__default__()
        default_gen.assert_called_once()

    def test_default_without_default_returns_not_found(self):
        page = RouterPage(path="/only", component=MagicMock(spec=ComponentGenerator))
        hist = MockHistoryPort(mode="hash")
        r = Router(page, history=hist)
        r._history._value = "/not-a-route"
        result = r.__default__()
        assert result == "Not Found"
