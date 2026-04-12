from webcompy.router._context import TypedRouterContext
from webcompy.router._router import Router


class TestTypedRouterContext:
    def test_create_instance(self):
        ctx = TypedRouterContext.__create_instance__(
            path="/test", state=None, query_params={"q": "1"}, path_params={"id": "42"}
        )
        assert ctx.path == "/test"
        assert ctx.query == {"q": "1"}
        assert ctx.path_params == {"id": "42"}

    def test_params_property(self):
        ctx = TypedRouterContext.__create_instance__(
            path="/test", state=None, query_params={"q": "1"}, path_params=None
        )
        assert ctx.params is None

    def test_params_empty_when_none(self):
        ctx = TypedRouterContext.__create_instance__(path="/", state=None, query_params=None, path_params=None)
        assert ctx.params is None

    def test_repr(self):
        ctx = TypedRouterContext.__create_instance__(path="/home", state=None, query_params=None, path_params=None)
        r = repr(ctx)
        assert "/home" in r

    def test_cannot_instantiate_directly(self):
        try:
            TypedRouterContext()
            raise AssertionError("Should have raised NotImplementedError")
        except NotImplementedError:
            pass


class TestRouterRouteMatching:
    def test_generate_route_matcher_exact(self):
        router = Router.__new__(Router)
        matcher = router._generate_route_matcher("/users")
        assert matcher("/users") is not None
        assert matcher("/posts") is None

    def test_generate_route_matcher_with_params(self):
        router = Router.__new__(Router)
        matcher = router._generate_route_matcher("/users/{id}")
        m = matcher("/users/42")
        assert m is not None
        assert m.group(1) == "42"

    def test_generate_route_matcher_no_match(self):
        router = Router.__new__(Router)
        matcher = router._generate_route_matcher("/users")
        assert matcher("/posts") is None
