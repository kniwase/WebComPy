from __future__ import annotations

import pytest

from webcompy.components._generator import define_component
from webcompy.testing import create_test_app


@define_component
def _ErrorTestRoot(context):
    from webcompy.elements import html

    return html.DIV({}, "test")


class TestAppDiScopeServerError:
    def test_app_di_scope_raises_attribute_error(self):
        app = create_test_app(root_component=_ErrorTestRoot)
        with pytest.raises(AttributeError, match="RenderContext"):
            _ = app.di_scope

    def test_app_provide_buffers_before_render_context(self):
        app = create_test_app(root_component=_ErrorTestRoot)
        app.provide("key", "value")
        assert len(app._deferred_ops) == 1
        ctx = app.create_render_context()
        assert len(app._deferred_ops) == 1
        ctx.dispose()

    def test_render_context_has_di_scope(self):
        app = create_test_app(root_component=_ErrorTestRoot)
        ctx = app.create_render_context()
        assert ctx.di_scope is not None
        ctx.dispose()

    def test_deferred_ops_applied_on_every_context(self):
        app = create_test_app(root_component=_ErrorTestRoot)
        app.set_head({"title": "First"})
        assert len(app._deferred_ops) == 1

        ctx1 = app.create_render_context()
        assert len(app._deferred_ops) == 1
        ctx1.dispose()

        ctx2 = app.create_render_context()
        assert len(app._deferred_ops) == 1
        ctx2.dispose()
