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
        ctx = app.create_render_context()
        assert app.routes is ctx._root.routes
        ctx.dispose()

    def test_router_mode_property(self):
        hist = MockHistoryPort(mode="hash")
        router = Router(history=hist)
        app = _make_app(router=router)
        assert app.router_mode == "hash"

    def test_set_path(self):
        hist = MockHistoryPort(mode="hash")
        router = Router(history=hist)
        app = _make_app(router=router)
        ctx = app.create_render_context("/test")
        app.set_path("/test")
        ctx.dispose()

    def test_style_property(self):
        app = _make_app()
        ctx = app.create_render_context()
        assert app.style is ctx._root.style
        ctx.dispose()

    def test_scripts_property(self):
        app = _make_app()
        ctx = app.create_render_context()
        assert app.scripts == ctx._root.scripts
        ctx.dispose()

    def test_head_property(self):
        app = _make_app()
        ctx = app.create_render_context()
        head = app.head
        assert "title" in head
        assert "meta" in head
        ctx.dispose()

    def test_set_title(self):
        app = _make_app()
        ctx = app.create_render_context()
        app.set_title("Test")
        ctx.dispose()

    def test_set_meta(self):
        app = _make_app()
        ctx = app.create_render_context()
        app.set_meta("charset", {"charset": "utf-8"})
        ctx.dispose()

    def test_append_link(self):
        app = _make_app()
        ctx = app.create_render_context()
        app.append_link({"rel": "stylesheet", "href": "/style.css"})
        ctx.dispose()

    def test_append_script(self):
        app = _make_app()
        ctx = app.create_render_context()
        app.append_script({"type": "text/javascript"}, "console.log('hi')")
        ctx.dispose()

    def test_set_head(self):
        app = _make_app()
        ctx = app.create_render_context()
        app.set_head({"title": "Test"})
        ctx.dispose()

    def test_update_head(self):
        app = _make_app()
        ctx = app.create_render_context()
        app.update_head({"title": "Test"})
        ctx.dispose()

    def test_no_router_routes_is_none(self):
        app = _make_app()
        assert app.routes is None

    def test_no_router_mode_is_none(self):
        app = _make_app()
        assert app.router_mode == "history"


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
        ctx1 = app1.create_render_context()
        ctx2 = app2.create_render_context()
        assert ctx1._component_store is not ctx2._component_store
        ctx1.dispose()
        ctx2.dispose()

    def test_app_store_is_provided_in_di(self):
        from webcompy.di._keys import _COMPONENT_STORE_KEY

        app = _make_app()
        ctx = app.create_render_context()
        from webcompy.di import inject

        store = inject(_COMPONENT_STORE_KEY)
        assert store is ctx._component_store
        ctx.dispose()

    def test_app_defer_depth_initial(self):
        app = _make_app()
        ctx = app.create_render_context()
        assert ctx._defer_depth == 0
        assert ctx._deferred_callbacks == []
        ctx.dispose()

    def test_two_apps_independent_defer_state(self):
        app1 = _make_app()
        app2 = _make_app()
        ctx1 = app1.create_render_context()
        ctx2 = app2.create_render_context()
        ctx1._defer_depth = 1
        assert ctx2._defer_depth == 0
        ctx1.dispose()
        ctx2.dispose()


class TestHtmlAttrs:
    def test_set_html_attr_returns_method(self):
        app = _make_app()
        ctx = app.create_render_context()
        assert app.set_html_attr is not None
        assert callable(app.set_html_attr)
        ctx.dispose()

    def test_remove_html_attr_returns_method(self):
        app = _make_app()
        ctx = app.create_render_context()
        assert app.remove_html_attr is not None
        assert callable(app.remove_html_attr)
        ctx.dispose()

    def test_html_attrs_property(self):
        app = _make_app()
        ctx = app.create_render_context()
        assert app.html_attrs == {}
        app.set_html_attr("lang", "ja")
        assert app.html_attrs == {"lang": "ja"}
        ctx.dispose()

    def test_set_and_get_html_attr(self):
        app = _make_app()
        ctx = app.create_render_context()
        app.set_html_attr("lang", "ja")
        assert app.html_attrs["lang"] == "ja"
        ctx.dispose()

    def test_remove_html_attr(self):
        app = _make_app()
        ctx = app.create_render_context()
        app.set_html_attr("data-test", "value")
        app.remove_html_attr("data-test")
        assert "data-test" not in app.html_attrs
        ctx.dispose()

    def test_html_attrs_with_computed(self):
        from webcompy.signal import Signal, computed

        app = _make_app()
        ctx = app.create_render_context()
        theme = Signal("light")
        app.set_html_attr("class", computed(lambda: theme.value))
        assert app.html_attrs["class"] == "light"
        theme.value = "dark"
        assert app.html_attrs["class"] == "dark"
        ctx.dispose()

    def test_html_attrs_per_app(self):
        app1 = _make_app()
        app2 = _make_app()
        ctx1 = app1.create_render_context()
        ctx2 = app2.create_render_context()
        app1.set_html_attr("lang", "ja")
        app2.set_html_attr("lang", "en")
        assert app1.html_attrs["lang"] == "ja"
        assert app2.html_attrs["lang"] == "en"
        ctx1.dispose()
        ctx2.dispose()

    def test_remove_html_attr_removes_computed_consumer(self):
        from webcompy.signal import Signal, computed

        app = _make_app()
        ctx = app.create_render_context()
        theme = Signal("light")
        app.set_html_attr("class", computed(lambda: theme.value))
        assert "class" not in ctx._root._callback_consumers
        app.remove_html_attr("class")
        assert "class" not in ctx._root._callback_consumers
        assert "class" not in ctx._root._html_attrs
        ctx.dispose()

    def test_consumer_destroy_called_when_overwriting_computed(self, monkeypatch):
        from webcompy.signal import Signal, computed

        app = _make_app()
        mock_dom = MagicMock()
        mock_dom.query_selector = MagicMock(return_value=MagicMock())
        from webcompy.ports._keys import DOM_PORT_KEY

        ctx = app.create_render_context()
        ctx.di_scope.provide(DOM_PORT_KEY, mock_dom)
        monkeypatch.setattr("webcompy.app._root_component.ENVIRONMENT", "pyscript")

        theme = Signal("light")
        c = computed(lambda: theme.value)
        app.set_html_attr("class", c)
        assert "class" in ctx._root._callback_consumers
        consumer1 = ctx._root._callback_consumers["class"]

        app.set_html_attr("class", "static")
        assert "class" not in ctx._root._callback_consumers

        app.set_html_attr("class", c)
        assert "class" in ctx._root._callback_consumers
        consumer2 = ctx._root._callback_consumers["class"]

        app.remove_html_attr("class")
        assert "class" not in ctx._root._callback_consumers
        assert "class" not in ctx._root._html_attrs

        assert consumer1 is not consumer2
        ctx.dispose()
