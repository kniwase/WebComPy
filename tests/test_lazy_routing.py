from __future__ import annotations

import sys
import types

from webcompy.components import ComponentGenerator, define_component
from webcompy.components._component import HeadPropsStore
from webcompy.components._generator import ComponentStore
from webcompy.di import DIScope
from webcompy.di._keys import _COMPONENT_STORE_KEY, _HEAD_PROPS_KEY
from webcompy.elements.types._dynamic import DynamicElement
from webcompy.router._lazy import LazyComponentGenerator, lazy
from webcompy.router._pages import WebComPyRouterException
from webcompy.router._router import Router


class _FakeComponent:
    pass


def _make_test_component(name="TestComponent"):
    from webcompy.elements import html

    def setup(ctx):
        return html.DIV({})

    return define_component(setup)


class TestLazyValidation:
    def test_missing_colon_raises(self):
        try:
            lazy("DocsPage", __file__)
        except WebComPyRouterException as e:
            assert "import_path must be 'module:Attribute' format" in str(e)
        else:
            raise AssertionError("Expected WebComPyRouterException")

    def test_empty_module_path_raises(self):
        try:
            lazy(":DocsPage", __file__)
        except WebComPyRouterException:
            pass
        else:
            raise AssertionError("Expected WebComPyRouterException")

    def test_empty_attribute_name_raises(self):
        try:
            lazy("myapp.pages:", __file__)
        except WebComPyRouterException:
            pass
        else:
            raise AssertionError("Expected WebComPyRouterException")

    def test_empty_caller_file_raises(self):
        try:
            lazy("module:Attr", "")
        except WebComPyRouterException:
            pass
        else:
            raise AssertionError("Expected WebComPyRouterException")

    def test_relative_module_path_raises(self):
        try:
            lazy(".pages.docs:DocsPage", __file__)
        except WebComPyRouterException as e:
            assert "relative module paths" in str(e)
        else:
            raise AssertionError("Expected WebComPyRouterException")

    def test_returns_component_generator(self):
        result = lazy("module:Attr", __file__)
        assert isinstance(result, ComponentGenerator)


class TestLazyComponentGenerator:
    def test_is_component_generator_instance(self):
        gen = lazy("module:Attr", __file__)
        assert isinstance(gen, ComponentGenerator)

    def test_is_lazy_component_generator(self):
        gen = lazy("module:Attr", __file__)
        assert isinstance(gen, LazyComponentGenerator)

    def test_resolve_imports_module(self):
        scope = DIScope()
        store = ComponentStore()
        scope.provide(_COMPONENT_STORE_KEY, store)
        scope.__enter__()

        try:
            comp = _make_test_component("TestComp")
            fake_module = types.ModuleType("fake_module")
            fake_module.TestComp = comp
            sys.modules["fake_module"] = fake_module

            gen = LazyComponentGenerator("fake_module:TestComp", __file__)
            resolved = gen._resolve()
            assert resolved is comp
        finally:
            scope.__exit__(None, None, None)

    def test_resolve_non_component_generator_raises(self):
        scope = DIScope()
        scope.__enter__()
        try:
            fake_module = types.ModuleType("fake_module2")
            fake_module2_name = "fake_module2"
            fake_module.SomeThing = _FakeComponent()
            sys.modules[fake_module2_name] = fake_module

            gen = LazyComponentGenerator(f"{fake_module2_name}:SomeThing", __file__)
            try:
                gen._resolve()
            except WebComPyRouterException as e:
                assert "not a ComponentGenerator" in str(e)
            else:
                raise AssertionError("Expected WebComPyRouterException")
        finally:
            scope.__exit__(None, None, None)

    def test_resolve_caches_result(self):
        scope = DIScope()
        store = ComponentStore()
        scope.provide(_COMPONENT_STORE_KEY, store)
        scope.__enter__()

        try:
            comp = _make_test_component("CachedComp")
            fake_module = types.ModuleType("cached_module")
            fake_module.CachedComp = comp
            sys.modules["cached_module"] = fake_module

            gen = LazyComponentGenerator("cached_module:CachedComp", __file__)
            r1 = gen._resolve()
            r2 = gen._resolve()
            assert r1 is r2
            assert gen._resolved is comp
        finally:
            scope.__exit__(None, None, None)

    def test_call_delegates_to_resolved(self):
        scope = DIScope()
        store = ComponentStore()
        scope.provide(_COMPONENT_STORE_KEY, store)
        head_props = HeadPropsStore()
        scope.provide(_HEAD_PROPS_KEY, head_props)
        scope.__enter__()

        try:
            comp = _make_test_component("CallComp")
            fake_module = types.ModuleType("call_module")
            fake_module.CallComp = comp
            sys.modules["call_module"] = fake_module

            gen = LazyComponentGenerator("call_module:CallComp", __file__)
            result = gen(None)
            assert result is not None
        finally:
            scope.__exit__(None, None, None)

    def test_preload_without_rendering(self):
        scope = DIScope()
        store = ComponentStore()
        scope.provide(_COMPONENT_STORE_KEY, store)
        scope.__enter__()

        try:
            comp = _make_test_component("PreloadComp")
            fake_module = types.ModuleType("preload_module")
            fake_module.PreloadComp = comp
            sys.modules["preload_module"] = fake_module

            gen = LazyComponentGenerator("preload_module:PreloadComp", __file__)
            gen._preload()
            assert gen._resolved is comp
        finally:
            scope.__exit__(None, None, None)

    def test_scoped_style_getter_delegates(self):
        scope = DIScope()
        store = ComponentStore()
        scope.provide(_COMPONENT_STORE_KEY, store)
        scope.__enter__()

        try:
            comp = _make_test_component("StyleComp")
            comp.scoped_style = {".test": {"color": "red"}}
            fake_module = types.ModuleType("style_module")
            fake_module.StyleComp = comp
            sys.modules["style_module"] = fake_module

            gen = LazyComponentGenerator("style_module:StyleComp", __file__)
            style = gen.scoped_style
            assert "color" in style
            assert "webcompy-cid" in style
        finally:
            scope.__exit__(None, None, None)

    def test_scoped_style_setter_delegates(self):
        scope = DIScope()
        store = ComponentStore()
        scope.provide(_COMPONENT_STORE_KEY, store)
        scope.__enter__()

        try:
            comp = _make_test_component("StyleSetComp")
            fake_module = types.ModuleType("styleset_module")
            fake_module.StyleSetComp = comp
            sys.modules["styleset_module"] = fake_module

            gen = LazyComponentGenerator("styleset_module:StyleSetComp", __file__)
            gen.scoped_style = {".btn": {"color": "blue"}}
            assert "color" in comp.scoped_style
        finally:
            scope.__exit__(None, None, None)

    def test_name_before_resolve(self):
        gen = LazyComponentGenerator("myapp.pages:TestPage", __file__)
        assert gen._name == "TestPage"

    def test_id_before_resolve(self):
        gen = LazyComponentGenerator("myapp.pages:TestPage", __file__)
        assert len(gen._id) == 32

    def test_none_registered_before_resolve(self):
        gen = LazyComponentGenerator("myapp.pages:TestPage", __file__)
        assert gen._registered is False


class TestRouterViewDynamicElement:
    def test_is_dynamic_element(self):
        from webcompy.di._keys import _ROUTER_KEY
        from webcompy.router._view import RouterView

        scope = DIScope()
        router = Router(preload=False)
        scope.provide(_ROUTER_KEY, router)
        scope.__enter__()
        try:
            view = RouterView()
            assert isinstance(view, DynamicElement)
        finally:
            scope.__exit__(None, None, None)

    def test_is_not_element(self):
        from webcompy.di._keys import _ROUTER_KEY
        from webcompy.router._view import RouterView

        scope = DIScope()
        router = Router(preload=False)
        scope.provide(_ROUTER_KEY, router)
        scope.__enter__()
        try:
            view = RouterView()
            from webcompy.elements.types._element import Element

            assert not isinstance(view, Element)
        finally:
            scope.__exit__(None, None, None)


class TestRouterPreload:
    def test_preload_lazy_routes_unresolved(self):
        scope = DIScope()
        store = ComponentStore()
        scope.provide(_COMPONENT_STORE_KEY, store)
        scope.__enter__()

        try:
            comp = _make_test_component("PreloadRoute")
            fake_module = types.ModuleType("preload_route_module")
            fake_module.PreloadRoute = comp
            sys.modules["preload_route_module"] = fake_module

            router = Router(
                {"path": "/", "component": lazy("preload_route_module:PreloadRoute", __file__)},
                preload=False,
            )
            gen = router._get_component_for_path("/")
            assert isinstance(gen, LazyComponentGenerator)
            assert gen._resolved is None

            router._preload = True
            router.preload_lazy_routes()

            gen = router._get_component_for_path("/")
            assert gen._resolved is comp
        finally:
            scope.__exit__(None, None, None)

    def test_preload_disabled_skips(self):
        scope = DIScope()
        scope.__enter__()
        try:
            comp = _make_test_component("SkipPreload")
            fake_module = types.ModuleType("skip_module")
            fake_module.SkipPreload = comp
            sys.modules["skip_module"] = fake_module

            router = Router(
                {"path": "/", "component": lazy("skip_module:SkipPreload", __file__)},
                preload=False,
            )
            gen = router._get_component_for_path("/")
            assert gen._resolved is None
        finally:
            scope.__exit__(None, None, None)


class TestRouterGetComponentForPath:
    def test_match_returns_component(self):
        scope = DIScope()
        scope.__enter__()
        try:
            comp = _make_test_component("MatchComp")
            fake_module = types.ModuleType("match_module")
            fake_module.MatchComp = comp
            sys.modules["match_module"] = fake_module

            router = Router(
                {"path": "/test", "component": comp},
                preload=False,
            )
            result = router._get_component_for_path("/test")
            assert result is comp
        finally:
            scope.__exit__(None, None, None)

    def test_no_match_returns_none(self):
        router = Router(preload=False)
        result = router._get_component_for_path("/nonexistent")
        assert result is None

    def test_match_with_path_params(self):
        scope = DIScope()
        scope.__enter__()
        try:
            comp = _make_test_component("ParamComp")
            fake_module = types.ModuleType("param_module")
            fake_module.ParamComp = comp
            sys.modules["param_module"] = fake_module

            router = Router(
                {"path": "/users/{id}", "component": comp},
                preload=False,
            )
            result = router._get_component_for_path("/users/42")
            assert result is comp
        finally:
            scope.__exit__(None, None, None)


class TestLazyPreloadMethod:
    def test_preload_resolves(self):
        scope = DIScope()
        store = ComponentStore()
        scope.provide(_COMPONENT_STORE_KEY, store)
        scope.__enter__()

        try:
            comp = _make_test_component("PLMethod")
            fake_module = types.ModuleType("pl_method")
            fake_module.PLMethod = comp
            sys.modules["pl_method"] = fake_module

            gen = LazyComponentGenerator("pl_method:PLMethod", __file__)
            gen._preload()
            assert gen._resolved is comp
        finally:
            scope.__exit__(None, None, None)


class TestRouterLinkMouseenter:
    def test_mouseenter_preloads_lazy_route(self):
        from webcompy.di._keys import _ROUTER_KEY
        from webcompy.router._link import RouterLink

        scope = DIScope()
        store = ComponentStore()
        scope.provide(_COMPONENT_STORE_KEY, store)
        head_props = HeadPropsStore()
        scope.provide(_HEAD_PROPS_KEY, head_props)

        comp = _make_test_component("HoverComp")
        fake_module = types.ModuleType("hover_module")
        fake_module.HoverComp = comp
        sys.modules["hover_module"] = fake_module

        lazy_gen = LazyComponentGenerator("hover_module:HoverComp", __file__)

        router = Router(
            {"path": "/target", "component": lazy_gen},
            preload=False,
        )
        scope.provide(_ROUTER_KEY, router)
        scope.__enter__()

        try:
            assert lazy_gen._resolved is None
            link = RouterLink(to="/target", text=["Go"])
            link._on_mouseenter()
            assert lazy_gen._resolved is comp
        finally:
            scope.__exit__(None, None, None)

    def test_mouseenter_noop_for_eager_route(self):
        from webcompy.di._keys import _ROUTER_KEY
        from webcompy.router._link import RouterLink

        scope = DIScope()
        store = ComponentStore()
        scope.provide(_COMPONENT_STORE_KEY, store)
        head_props = HeadPropsStore()
        scope.provide(_HEAD_PROPS_KEY, head_props)

        comp = _make_test_component("EagerComp")
        router = Router(
            {"path": "/eager", "component": comp},
            preload=False,
        )
        scope.provide(_ROUTER_KEY, router)
        scope.__enter__()

        try:
            link = RouterLink(to="/eager", text=["Go"])
            result = link._on_mouseenter()
            assert result is None
        finally:
            scope.__exit__(None, None, None)

    def test_mouseenter_strips_query_and_hash(self):
        from webcompy.di._keys import _ROUTER_KEY
        from webcompy.router._link import RouterLink

        scope = DIScope()
        store = ComponentStore()
        scope.provide(_COMPONENT_STORE_KEY, store)
        head_props = HeadPropsStore()
        scope.provide(_HEAD_PROPS_KEY, head_props)

        comp = _make_test_component("QueryComp")
        fake_module = types.ModuleType("query_module")
        fake_module.QueryComp = comp
        sys.modules["query_module"] = fake_module

        lazy_gen = LazyComponentGenerator("query_module:QueryComp", __file__)

        router = Router(
            {"path": "/page", "component": lazy_gen},
            preload=False,
        )
        scope.provide(_ROUTER_KEY, router)
        scope.__enter__()

        try:
            link = RouterLink(to="/page?x=1#sec", text=["Go"])
            link._on_mouseenter()
            assert lazy_gen._resolved is comp
        finally:
            scope.__exit__(None, None, None)

    def test_get_component_for_path_with_base_url(self):
        scope = DIScope()
        store = ComponentStore()
        scope.provide(_COMPONENT_STORE_KEY, store)

        comp = _make_test_component("BaseComp")
        fake_module = types.ModuleType("base_module")
        fake_module.BaseComp = comp
        sys.modules["base_module"] = fake_module

        lazy_gen = LazyComponentGenerator("base_module:BaseComp", __file__)

        router = Router(
            {"path": "/page", "component": lazy_gen},
            mode="history",
            base_url="myapp",
            preload=False,
        )
        assert router._get_component_for_path("/myapp/page") is lazy_gen
