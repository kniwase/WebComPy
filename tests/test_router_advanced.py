from unittest.mock import MagicMock

from webcompy.components import ComponentGenerator, WebComPyComponentException
from webcompy.router._pages import RouterPage
from webcompy.router._router import Router


class TestRouterSingleton:
    def test_only_one_instance_allowed(self):
        page = RouterPage(path="/", component=MagicMock(spec=ComponentGenerator))
        _r1 = Router(page, mode="hash")
        try:
            Router(page, mode="hash")
            raise AssertionError("Should have raised")
        except WebComPyComponentException:
            pass

    def test_second_instance_after_reset(self):
        page = RouterPage(path="/", component=MagicMock(spec=ComponentGenerator))
        r1 = Router(page, mode="hash")
        Router._instance = None
        r2 = Router(page, mode="history")
        assert r2 is not r1


class TestRouterInit:
    def test_init_sets_mode(self):
        page = RouterPage(path="/", component=MagicMock(spec=ComponentGenerator))
        r = Router(page, mode="hash")
        assert r.__mode__ == "hash"

    def test_init_strips_base_url(self):
        page = RouterPage(path="/", component=MagicMock(spec=ComponentGenerator))
        r = Router(page, mode="history", base_url="/app/")
        assert r.__base_url__ == "app"


class TestRouterRouteGeneration:
    def test_generate_routes(self):
        page = RouterPage(path="/users", component=MagicMock(spec=ComponentGenerator))
        r = Router(page, mode="hash")
        assert len(r.__routes__) == 1
        path_str, _matcher, _param_names, _component, _page_obj = r.__routes__[0]
        assert path_str == "users"

    def test_generate_routes_with_params(self):
        page = RouterPage(path="/users/{id}", component=MagicMock(spec=ComponentGenerator))
        r = Router(page, mode="hash")
        _path_str, _matcher, param_names, _component, _page_obj = r.__routes__[0]
        assert "id" in param_names


class TestRouterGetCurrentPath:
    def test_get_current_path_no_query(self):
        page = RouterPage(path="/", component=MagicMock(spec=ComponentGenerator))
        r = Router(page, mode="hash")
        r._location._value = "/home"
        pathname, search = r._get_current_path()
        assert pathname == "/home"
        assert search == ""

    def test_get_current_path_with_query(self):
        page = RouterPage(path="/", component=MagicMock(spec=ComponentGenerator))
        r = Router(page, mode="hash")
        r._location._value = "/home?key=val&foo=bar"
        pathname, search = r._get_current_path()
        assert pathname == "/home"
        assert search == "key=val&foo=bar"


class TestRouterGenerateRouterContext:
    def test_context_with_query(self):
        page = RouterPage(path="/", component=MagicMock(spec=ComponentGenerator))
        r = Router(page, mode="hash")
        ctx = r._generate_router_context("/search", "q=hello&page=1", None, [])
        assert ctx.query == {"q": "hello", "page": "1"}

    def test_context_empty_query(self):
        page = RouterPage(path="/", component=MagicMock(spec=ComponentGenerator))
        r = Router(page, mode="hash")
        ctx = r._generate_router_context("/home", "", None, [])
        assert ctx.query == {}

    def test_context_with_path_params(self):
        page = RouterPage(path="/users/{id}", component=MagicMock(spec=ComponentGenerator))
        r = Router(page, mode="hash")
        import re

        match = re.match(r"([^/]*?)$", "42")
        ctx = r._generate_router_context("/users/42", "", match, ["id"])
        assert ctx.path_params == {"id": "42"}

    def test_context_without_path_params(self):
        page = RouterPage(path="/", component=MagicMock(spec=ComponentGenerator))
        r = Router(page, mode="hash")
        ctx = r._generate_router_context("/home", "", None, [])
        assert ctx.path_params == {}


class TestRouterSetPath:
    def test_set_path_delegates_to_location(self):
        page = RouterPage(path="/", component=MagicMock(spec=ComponentGenerator))
        r = Router(page, mode="hash")
        r.__set_path__("/new/path", {"key": "val"})
        assert r._location._value == "/new/path"


class TestRouterDefault:
    def test_default_with_default_component(self):
        _mock_gen = MagicMock(spec=ComponentGenerator)
        page = RouterPage(path="/nonexistent", component=MagicMock(spec=ComponentGenerator))
        default_gen = MagicMock(spec=ComponentGenerator)
        r = Router(page, default=default_gen, mode="hash")
        r._location._value = "/not-a-route"
        r.__default__()
        default_gen.assert_called_once()

    def test_default_without_default_returns_not_found(self):
        page = RouterPage(path="/only", component=MagicMock(spec=ComponentGenerator))
        r = Router(page, mode="hash")
        r._location._value = "/not-a-route"
        result = r.__default__()
        assert result == "Not Found"
