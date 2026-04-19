import warnings

import pytest

from webcompy.app._app import WebComPyApp
from webcompy.app._config import AppConfig
from webcompy.app._root_component import AppDocumentRoot
from webcompy.cli._config import WebComPyConfig
from webcompy.components._generator import define_component
from webcompy.router import Router


@define_component
def DummyRoot(context):
    from webcompy.elements import html

    return html.DIV({}, "hello")


def _make_app(**kwargs):
    return WebComPyApp(root_component=DummyRoot, **kwargs)


class TestWebComPyAppConfig:
    def test_default_config(self):
        app = _make_app()
        assert app.config.base_url == "/"
        assert app.config.dependencies == []
        assert app.config.assets is None

    def test_custom_config(self):
        config = AppConfig(base_url="/myapp", dependencies=["numpy"])
        app = _make_app(config=config)
        assert app.config.base_url == "/myapp/"
        assert app.config.dependencies == ["numpy"]

    def test_config_stored(self):
        config = AppConfig()
        app = _make_app(config=config)
        assert app.config is config


class TestWebComPyAppComponentDeprecation:
    def test_component_deprecation_warning(self):
        app = _make_app()
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            root = app.__component__
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)
            assert "__component__" in str(w[0].message)
        assert isinstance(root, AppDocumentRoot)


class TestWebComPyAppForwarding:
    def test_routes_property(self):
        router = Router(mode="hash")
        app = _make_app(router=router)
        assert app.routes is app.__component__.routes

    def test_router_mode_property(self):
        router = Router(mode="hash")
        app = _make_app(router=router)
        assert app.router_mode == "hash"

    def test_set_path(self):
        router = Router(mode="hash")
        app = _make_app(router=router)
        app.set_path("/test")

    def test_style_property(self):
        app = _make_app()
        assert app.style is app.__component__.style

    def test_scripts_property(self):
        app = _make_app()
        assert app.scripts == app.__component__.scripts

    def test_head_property(self):
        app = _make_app()
        head = app.head
        assert "title" in head
        assert "meta" in head

    def test_set_title(self):
        app = _make_app()
        app.set_title("Test")

    def test_set_meta(self):
        app = _make_app()
        app.set_meta("charset", {"charset": "utf-8"})

    def test_append_link(self):
        app = _make_app()
        app.append_link({"rel": "stylesheet", "href": "/style.css"})

    def test_append_script(self):
        app = _make_app()
        app.append_script({"type": "text/javascript"}, "console.log('hi')")

    def test_set_head(self):
        app = _make_app()
        app.set_head({"title": "Test"})

    def test_update_head(self):
        app = _make_app()
        app.update_head({"title": "Test"})

    def test_no_router_routes_is_none(self):
        app = _make_app()
        assert app.routes is None

    def test_no_router_mode_is_none(self):
        app = _make_app()
        assert app.router_mode is None


class TestWebComPyAppRun:
    def test_run_raises_outside_browser(self):
        from webcompy.exception import WebComPyException

        app = _make_app()
        with pytest.raises(WebComPyException):
            app.run()


class TestPerAppComponentStore:
    def test_two_apps_have_separate_stores(self):
        app1 = _make_app()
        app2 = _make_app()
        assert app1._component_store is not app2._component_store

    def test_app_store_is_provided_in_di(self):
        from webcompy.di._keys import _COMPONENT_STORE_KEY

        app = _make_app()
        with app.di_scope:
            from webcompy.di import inject

            store = inject(_COMPONENT_STORE_KEY)
            assert store is app._component_store

    def test_app_defer_depth_initial(self):
        app = _make_app()
        assert app._defer_depth == 0
        assert app._deferred_callbacks == []

    def test_two_apps_independent_defer_state(self):
        app1 = _make_app()
        app2 = _make_app()
        app1._defer_depth = 1
        assert app2._defer_depth == 0


class TestDeprecationWarnings:
    def test_webcompy_config_deprecation(self):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            WebComPyConfig(app_package=".")
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)
            assert "WebComPyConfig" in str(w[0].message)

    def test_component_deprecation_warning(self):
        app = _make_app()
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            _ = app.__component__
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)
