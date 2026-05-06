from __future__ import annotations

from webcompy.app._app import WebComPyApp
from webcompy.app._config import AppConfig, PluginScript
from webcompy.cli._html import generate_html
from webcompy.plugin._manager import PluginManager
from webcompy.plugin._plugin import WebComPyPlugin, WebComPyPluginException
from webcompy.router._router import Router


class _TestApp:
    def __init__(self, plugins: list[str] | None = None):
        from webcompy.components._generator import define_component
        from webcompy.elements import html

        @define_component
        def _TestRoot(context):
            return html.DIV({}, "test")

        config = AppConfig(app_package=".", plugins=plugins or [])
        self.app = WebComPyApp(root_component=_TestRoot, config=config)


class TestWebComPyPlugin:
    def test_defaults(self):
        assert WebComPyPlugin.name == ""
        assert WebComPyPlugin.version == "0.1.0"
        assert WebComPyPlugin.get_providers() == {}
        assert WebComPyPlugin.get_scripts() == []

    def test_subclass_overrides(self):
        class MyPlugin(WebComPyPlugin):
            name = "my-plugin"

            @staticmethod
            def get_providers():
                return {"key": "value"}

        assert MyPlugin.name == "my-plugin"
        assert MyPlugin.get_providers() == {"key": "value"}

    def test_get_scripts_returns_plugin_scripts(self):
        class ScriptedPlugin(WebComPyPlugin):
            @staticmethod
            def get_scripts():
                return [
                    PluginScript(attrs={"src": "foo.js"}),
                    PluginScript(attrs={"src": "bar.js"}),
                ]

        scripts = ScriptedPlugin.get_scripts()
        assert len(scripts) == 2
        assert scripts[0].attrs["src"] == "foo.js"
        assert scripts[1].attrs["src"] == "bar.js"

    def test_on_app_init_is_noop_by_default(self):
        plugin = WebComPyPlugin()
        obj = object()
        plugin.on_app_init(obj)  # should not raise

    def test_on_app_ready_is_noop_by_default(self):
        plugin = WebComPyPlugin()
        obj = object()
        plugin.on_app_ready(obj)  # should not raise


class TestPluginManager:
    def test_discovery_valid_path(self):
        import sys

        test_module = sys.modules[__name__]
        test_module.TestPluginForDiscovery = type("TestPluginForDiscovery", (WebComPyPlugin,), {})
        try:
            test_app = _TestApp()
            pm = PluginManager(test_app.app)
            pm.discover(["tests.test_plugin_system:TestPluginForDiscovery"])
            assert len(pm._plugin_classes) == 1
        finally:
            delattr(test_module, "TestPluginForDiscovery")

    def test_discovery_invalid_path_no_colon(self):
        test_app = _TestApp()
        pm = PluginManager(test_app.app)
        try:
            pm.discover(["invalid_path"])
            raise AssertionError("expected exception")
        except WebComPyPluginException as e:
            assert "missing ':' separator" in str(e)

    def test_discovery_invalid_path_empty_module(self):
        test_app = _TestApp()
        pm = PluginManager(test_app.app)
        try:
            pm.discover([":ClassName"])
            raise AssertionError("expected exception")
        except WebComPyPluginException:
            pass

    def test_discovery_non_plugin_class(self):
        class NotAPlugin:
            pass

        import sys

        test_module = sys.modules[__name__]
        test_module.NotAPlugin = NotAPlugin
        try:
            test_app = _TestApp()
            pm = PluginManager(test_app.app)
            try:
                pm.discover(["tests.test_plugin_system:NotAPlugin"])
                raise AssertionError("expected exception")
            except WebComPyPluginException:
                pass
        finally:
            delattr(test_module, "NotAPlugin")

    def test_init_all_registers_providers(self):
        class ProviderPlugin(WebComPyPlugin):
            @staticmethod
            def get_providers():
                return {"my_key": "my_value"}

        test_app = _TestApp()
        pm = PluginManager(test_app.app)
        import sys

        test_module = sys.modules[__name__]
        test_module.ProviderPlugin = ProviderPlugin
        try:
            pm.discover(["tests.test_plugin_system:ProviderPlugin"])
            pm.init_all()
            from webcompy.di import inject

            with test_app.app.di_scope:
                assert inject("my_key") == "my_value"
        finally:
            delattr(test_module, "ProviderPlugin")

    def test_init_all_calls_on_app_init(self):
        called: list[WebComPyApp | None] = []

        class InitPlugin(WebComPyPlugin):
            def on_app_init(self, app):
                called.append(app)

        test_app = _TestApp()
        pm = PluginManager(test_app.app)
        import sys

        test_module = sys.modules[__name__]
        test_module.InitPlugin = InitPlugin
        try:
            pm.discover(["tests.test_plugin_system:InitPlugin"])
            pm.init_all()
            assert len(called) == 1
            assert called[0] is test_app.app
        finally:
            delattr(test_module, "InitPlugin")

    def test_scripts_collected_from_plugins(self):
        class ScriptedPlugin(WebComPyPlugin):
            @staticmethod
            def get_scripts():
                return [PluginScript(attrs={"src": "baz.js"})]

        test_app = _TestApp()
        pm = PluginManager(test_app.app)
        import sys

        test_module = sys.modules[__name__]
        test_module.ScriptedPlugin = ScriptedPlugin
        try:
            pm.discover(["tests.test_plugin_system:ScriptedPlugin"])
            scripts = pm.scripts
            assert len(scripts) == 1
            assert scripts[0].attrs["src"] == "baz.js"
        finally:
            delattr(test_module, "ScriptedPlugin")

    def test_empty_plugins_list_is_noop(self):
        test_app = _TestApp(plugins=[])
        pm = PluginManager(test_app.app)
        pm.discover([])
        pm.init_all()
        assert pm.scripts == []


class TestGenerateHtmlWithPluginScripts:
    def test_plugin_manager_scripts_included(self):
        class PluginForHtml(WebComPyPlugin):
            @staticmethod
            def get_scripts():
                return [
                    PluginScript(
                        attrs={"type": "text/javascript", "src": "https://example.com/plugin.js"},
                        condition="location.search.includes('debug')",
                    )
                ]

        import sys

        test_module = sys.modules[__name__]
        test_module.PluginForHtml = PluginForHtml
        try:
            test_app = _TestApp(plugins=["tests.test_plugin_system:PluginForHtml"])
            html_str = generate_html(
                test_app.app,
                dev_mode=False,
                prerender=False,
                app_version="0.0.0",
                wheel_filename="test_pkg-0+sha.abcdef12-py3-none-any.whl",
            )
            assert "https://example.com/plugin.js" in html_str
            assert "location.search.includes('debug')" in html_str
        finally:
            delattr(test_module, "PluginForHtml")


class TestRouterHooks:
    def test_before_route_change_cancel(self):
        router = Router(mode="hash")
        cancelled: list[bool] = []

        def guard(from_path, to_path):
            if "/admin" in to_path:
                return False
            return None

        router.before_route_change.append(guard)
        router.after_route_change.append(lambda p: cancelled.append(False))
        router.__set_path__("/admin", {})
        assert len(cancelled) == 0

    def test_before_route_change_allow(self):
        router = Router(mode="hash")
        navigated: list[str] = []

        def guard(from_path, to_path):
            return True

        router.before_route_change.append(guard)
        router.after_route_change.append(navigated.append)
        router.__set_path__("/about", {})
        assert len(navigated) == 1
        assert navigated[0] == "/about"

    def test_multiple_guards_short_circuit(self):
        router = Router(mode="hash")
        second_called = False

        def guard_a(from_path, to_path):
            return False

        def guard_b(from_path, to_path):
            nonlocal second_called
            second_called = True
            return True

        router.before_route_change.extend([guard_a, guard_b])
        router.__set_path__("/blocked", {})
        assert not second_called

    def test_on_route_error_suppress(self):
        class BadRouter(Router):
            def __init__(self):
                from collections.abc import Callable
                from re import Match

                self._location = type("Loc", (), {"_value": "/"})()
                matcher: Callable[[str], Match[str] | None] = lambda _: None
                self.__routes__ = [
                    ("/test", matcher, [], type("DummyGen", (), {"_instance_id": ""})(), {}),
                ]
                self.before_route_change = []
                self.after_route_change = []
                self.on_route_error = []

            def _get_elements_generator(self, args):
                raise ValueError("test error")

        router = BadRouter()
        suppressed = False

        def handler(e):
            nonlocal suppressed
            suppressed = True
            return True

        router.on_route_error.append(handler)
        _ = router.__cases__
        assert suppressed

    def test_on_route_error_propagate(self):
        class BadRouter(Router):
            def __init__(self):
                from collections.abc import Callable
                from re import Match

                self._location = type("Loc", (), {"_value": "/"})()
                matcher: Callable[[str], Match[str] | None] = lambda _: None
                self.__routes__ = [
                    ("/test", matcher, [], type("DummyGen", (), {"_instance_id": ""})(), {}),
                ]
                self.before_route_change = []
                self.after_route_change = []
                self.on_route_error = []

            def _get_elements_generator(self, args):
                raise ValueError("test error")

        router = BadRouter()
        called = False

        def handler(e):
            nonlocal called
            called = True
            return False

        import pytest

        router.on_route_error.append(handler)
        with pytest.raises(ValueError):
            _ = router.__cases__
        assert called
