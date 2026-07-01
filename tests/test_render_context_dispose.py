from __future__ import annotations

from webcompy.components._generator import define_component
from webcompy_testing import create_test_app


@define_component
def _DisposeTestRoot(context):
    from webcompy.elements import html

    return html.DIV({}, "hello")


class TestRenderContextDispose:
    def test_dispose_clears_references(self):
        app = create_test_app(root_component=_DisposeTestRoot)
        ctx = app.create_render_context()
        assert ctx._root is not None
        assert ctx._di_scope is not None
        assert ctx._component_store is not None

        ctx.dispose()

        assert ctx._root is None
        assert ctx._di_scope is None
        assert ctx._component_store is None
        assert ctx._router is None

    def test_dispose_disposes_di_scope(self):
        app = create_test_app(root_component=_DisposeTestRoot)
        ctx = app.create_render_context()
        di_scope = ctx._di_scope

        ctx.dispose()
        assert di_scope._disposed is True

    def test_di_scope_children_disposed(self):
        app = create_test_app(root_component=_DisposeTestRoot)
        ctx = app.create_render_context()
        di_scope = ctx._di_scope
        child = di_scope.create_child()

        ctx.dispose()
        assert di_scope._disposed is True
        assert child._disposed is True

    def test_dispose_marks_di_scope_disposed(self):
        app = create_test_app(root_component=_DisposeTestRoot)
        ctx = app.create_render_context()
        ctx.dispose()
