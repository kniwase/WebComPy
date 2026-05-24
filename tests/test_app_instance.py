from unittest.mock import MagicMock

import pytest

from tests.conftest import MockHistoryPort
from webcompy.app._app import WebComPyApp
from webcompy.app._config import WebComPyAppConfig
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
        assert app.config.selector == "#webcompy-app"
        assert app.config.profile is False

    def test_custom_config(self):
        config = WebComPyAppConfig(base_url="/myapp", selector="#custom")
        app = _make_app(config=config)
        assert app.config.base_url == "/myapp/"
        assert app.config.selector == "#custom"

    def test_config_stored(self):
        config = WebComPyAppConfig()
        app = _make_app(config=config)
        assert app.config is config


class TestWebComPyAppForwarding:
    def test_routes_property(self):
        hist = MockHistoryPort(mode="hash")
        router = Router(history=hist)
        app = _make_app(router=router)
        assert app.routes is app._root.routes

    def test_router_mode_property(self):
        hist = MockHistoryPort(mode="hash")
        router = Router(history=hist)
        app = _make_app(router=router)
        assert app.router_mode == "hash"

    def test_set_path(self):
        hist = MockHistoryPort(mode="hash")
        router = Router(history=hist)
        app = _make_app(router=router)
        app.set_path("/test")

    def test_style_property(self):
        app = _make_app()
        assert app.scoped_styles == app._root.scoped_styles

    def test_scripts_property(self):
        app = _make_app()
        assert app.scripts == app._root.scripts

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


class TestHtmlAttrs:
    def test_set_html_attr_returns_method(self):
        app = _make_app()
        assert app.set_html_attr is not None
        assert callable(app.set_html_attr)

    def test_remove_html_attr_returns_method(self):
        app = _make_app()
        assert app.remove_html_attr is not None
        assert callable(app.remove_html_attr)

    def test_html_attrs_property(self):
        app = _make_app()
        assert app.html_attrs == {}
        app.set_html_attr("lang", "ja")
        assert app.html_attrs == {"lang": "ja"}

    def test_set_and_get_html_attr(self):
        app = _make_app()
        app.set_html_attr("lang", "ja")
        assert app.html_attrs["lang"] == "ja"

    def test_remove_html_attr(self):
        app = _make_app()
        app.set_html_attr("data-test", "value")
        app.remove_html_attr("data-test")
        assert "data-test" not in app.html_attrs

    def test_html_attrs_with_computed(self):
        from webcompy.signal import Signal, computed

        app = _make_app()
        theme = Signal("light")
        app.set_html_attr("class", computed(lambda: theme.value))
        assert app.html_attrs["class"] == "light"
        theme.value = "dark"
        assert app.html_attrs["class"] == "dark"

    def test_html_attrs_per_app(self):
        app1 = _make_app()
        app2 = _make_app()
        app1.set_html_attr("lang", "ja")
        app2.set_html_attr("lang", "en")
        assert app1.html_attrs["lang"] == "ja"
        assert app2.html_attrs["lang"] == "en"

    def test_remove_html_attr_removes_computed_consumer(self):
        from webcompy.signal import Signal, computed

        app = _make_app()
        theme = Signal("light")
        app.set_html_attr("class", computed(lambda: theme.value))
        assert "class" not in app._root._callback_consumers
        app.remove_html_attr("class")
        assert "class" not in app._root._callback_consumers
        assert "class" not in app._root._html_attrs

    def test_consumer_destroy_called_when_overwriting_computed(self, monkeypatch):
        from webcompy.signal import Signal, computed

        app = _make_app()
        mock_dom = MagicMock()
        mock_dom.query_selector = MagicMock(return_value=MagicMock())
        from webcompy.ports._keys import DOM_PORT_KEY

        app._di_scope.provide(DOM_PORT_KEY, mock_dom)
        monkeypatch.setattr("webcompy.app._root_component.ENVIRONMENT", "pyscript")

        with app._di_scope:
            theme = Signal("light")
            c = computed(lambda: theme.value)
            app.set_html_attr("class", c)
            assert "class" in app._root._callback_consumers
            consumer1 = app._root._callback_consumers["class"]

            app.set_html_attr("class", "static")
            assert "class" not in app._root._callback_consumers

            app.set_html_attr("class", c)
            assert "class" in app._root._callback_consumers
            consumer2 = app._root._callback_consumers["class"]

            app.remove_html_attr("class")
            assert "class" not in app._root._callback_consumers
            assert "class" not in app._root._html_attrs

            assert consumer1 is not consumer2
