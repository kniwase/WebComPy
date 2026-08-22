from __future__ import annotations

from webcompy.components._component import _active_app_context, _get_app_instance
from webcompy.components._generator import define_component
from webcompy.di._scope import _active_di_scope, _get_app_di_scope
from webcompy_testing import create_test_app


@define_component("dispose-test-root")
def DisposeTestRoot(context):
    from webcompy.elements import html

    return html.DIV({}, "hello")


class TestRenderContextDispose:
    def test_dispose_clears_references(self):
        app = create_test_app(root_component=DisposeTestRoot)
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
        app = create_test_app(root_component=DisposeTestRoot)
        ctx = app.create_render_context()
        di_scope = ctx._di_scope

        ctx.dispose()
        assert di_scope._disposed is True

    def test_di_scope_children_disposed(self):
        app = create_test_app(root_component=DisposeTestRoot)
        ctx = app.create_render_context()
        di_scope = ctx._di_scope
        child = di_scope.create_child()

        ctx.dispose()
        assert di_scope._disposed is True
        assert child._disposed is True

    def test_dispose_marks_di_scope_disposed(self):
        app = create_test_app(root_component=DisposeTestRoot)
        ctx = app.create_render_context()
        ctx.dispose()

    def test_overlapping_contexts_disposed_lifo_leave_no_active_context(self):
        app = create_test_app(root_component=DisposeTestRoot)
        ctx1 = app.create_render_context()
        ctx2 = app.create_render_context()
        ctx2.dispose()
        assert _active_app_context.get() is ctx1
        assert _active_di_scope.get(None) is ctx1._di_scope
        assert app._render_context_cv.get() is ctx1
        ctx1.dispose()
        assert _active_app_context.get() is None
        assert _active_di_scope.get(None) is None
        assert app._render_context_cv.get() is None

    def test_overlapping_contexts_disposed_creation_order_leave_context_vars_clear(self):
        app = create_test_app(root_component=DisposeTestRoot)
        ctx1 = app.create_render_context()
        ctx2 = app.create_render_context()
        ctx1.dispose()
        assert _active_app_context.get() is ctx2
        assert _active_di_scope.get(None) is ctx2._di_scope
        assert app._render_context_cv.get() is ctx2
        ctx2.dispose()
        assert _active_app_context.get() is None
        assert _active_di_scope.get(None) is None
        assert app._render_context_cv.get() is None


class TestBrowserFallbackRestore:
    def test_newest_disposed_restores_previous_fallback(self, monkeypatch):
        monkeypatch.setattr("webcompy.app._render_context.ENVIRONMENT", "pyscript")
        app = create_test_app(root_component=DisposeTestRoot)
        ctx1 = app.create_render_context()
        ctx2 = app.create_render_context()
        assert _get_app_instance() is ctx2
        assert _get_app_di_scope() is ctx2._di_scope
        ctx2.dispose()
        assert _get_app_instance() is ctx1
        assert _get_app_di_scope() is ctx1._di_scope
        ctx1.dispose()
        assert _get_app_instance() is None
        assert _get_app_di_scope() is None

    def test_oldest_disposed_keeps_surviving_fallback(self, monkeypatch):
        monkeypatch.setattr("webcompy.app._render_context.ENVIRONMENT", "pyscript")
        app = create_test_app(root_component=DisposeTestRoot)
        ctx1 = app.create_render_context()
        ctx2 = app.create_render_context()
        ctx1.dispose()
        assert _get_app_instance() is ctx2
        assert _get_app_di_scope() is ctx2._di_scope
        ctx2.dispose()
        assert _get_app_instance() is None
        assert _get_app_di_scope() is None

    def test_last_dispose_walks_past_disposed_fallback_chain(self, monkeypatch):
        monkeypatch.setattr("webcompy.app._render_context.ENVIRONMENT", "pyscript")
        app = create_test_app(root_component=DisposeTestRoot)
        ctx1 = app.create_render_context()
        ctx2 = app.create_render_context()
        ctx1.dispose()
        ctx2.dispose()
        assert _get_app_instance() is None
        assert _get_app_di_scope() is None
