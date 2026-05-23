from __future__ import annotations

import sys

from webcompy.app._app import WebComPyApp
from webcompy.app._config import WebComPyAppConfig
from webcompy.components._generator import define_component
from webcompy.plugin._manager import PluginManager
from webcompy.plugin._plugin import WebComPyPlugin


@define_component
def _PluginTestRoot(context):
    from webcompy.elements import html

    return html.DIV({}, "test")


class _InitCountingPlugin(WebComPyPlugin):
    def __init__(self):
        super().__init__()
        self.init_count = 0

    def on_render_context_init(self, ctx):
        self.init_count += 1


class TestPluginRenderContextInit:
    def test_on_render_context_init_called_per_request(self):
        import sys

        test_module = sys.modules[__name__]
        test_module._InitCountingPlugin = _InitCountingPlugin
        try:
            app = WebComPyApp(
                root_component=_PluginTestRoot,
                config=WebComPyAppConfig(plugins=["tests.test_plugin_render_context_init:_InitCountingPlugin"]),
            )
            ctx1 = app.create_render_context()
            ctx2 = app.create_render_context()

            instances = app._plugin_manager._plugin_instances
            assert len(instances) == 1
            assert instances[0].init_count == 2

            ctx1.dispose()
            ctx2.dispose()
        finally:
            delattr(test_module, "_InitCountingPlugin")

    def test_on_render_context_init_with_manual_manager(self):
        class ManualInitPlugin(WebComPyPlugin):
            def __init__(self):
                super().__init__()
                self.init_count = 0

            def on_render_context_init(self, ctx):
                self.init_count += 1

        app = WebComPyApp(
            root_component=_PluginTestRoot,
            config=WebComPyAppConfig(),
        )
        pm = PluginManager(app)

        test_module = sys.modules[__name__]
        test_module._ManualInitPlugin = ManualInitPlugin
        try:
            pm.discover(["tests.test_plugin_render_context_init:_ManualInitPlugin"])
            pm.init_all()

            ctx1 = app.create_render_context()
            pm.init_render_context(ctx1)
            ctx2 = app.create_render_context()
            pm.init_render_context(ctx2)

            assert pm._plugin_instances[0].init_count == 2

            ctx1.dispose()
            ctx2.dispose()
        finally:
            delattr(test_module, "_ManualInitPlugin")
