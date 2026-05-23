from __future__ import annotations

import pytest

from webcompy.app._app import WebComPyApp
from webcompy.app._config import WebComPyAppConfig
from webcompy.components._generator import define_component


@define_component
def _ErrorTestRoot(context):
    from webcompy.elements import html

    return html.DIV({}, "test")


class TestAppDiScopeServerError:
    def test_app_di_scope_raises_attribute_error(self):
        app = WebComPyApp(
            root_component=_ErrorTestRoot,
            config=WebComPyAppConfig(),
        )
        with pytest.raises(AttributeError, match="RenderContext"):
            _ = app.di_scope

    def test_app_provide_buffers_before_render_context(self):
        app = WebComPyApp(
            root_component=_ErrorTestRoot,
            config=WebComPyAppConfig(),
        )
        app.provide("key", "value")
        assert len(app._deferred_ops) == 1
        ctx = app.create_render_context()
        assert len(app._deferred_ops) == 0
        ctx.dispose()

    def test_render_context_has_di_scope(self):
        app = WebComPyApp(
            root_component=_ErrorTestRoot,
            config=WebComPyAppConfig(),
        )
        ctx = app.create_render_context()
        assert ctx.di_scope is not None
        ctx.dispose()
