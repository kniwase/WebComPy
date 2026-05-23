from __future__ import annotations

from webcompy.app._app import WebComPyApp
from webcompy.app._config import WebComPyAppConfig
from webcompy.cli._html import generate_html
from webcompy.components._generator import define_component


@define_component
def _IsolationRoot(context):
    from webcompy.elements import html

    return html.DIV({}, "content")


class TestRequestIsolation:
    def test_contexts_produce_independent_html(self):
        app = WebComPyApp(
            root_component=_IsolationRoot,
            config=WebComPyAppConfig(),
        )

        ctx1 = app.create_render_context("/page-a")
        ctx1.set_title("Page A")
        ctx1.append_link({"rel": "stylesheet", "href": "/a.css"})
        html1 = generate_html(
            ctx1,
            app_package_name="test_pkg",
            dev_mode=False,
            prerender=True,
            app_version="0.0.0",
            wheel_filename="test.whl",
        )
        ctx1.dispose()

        ctx2 = app.create_render_context("/page-b")
        ctx2.set_title("Page B")
        ctx2.append_link({"rel": "stylesheet", "href": "/b.css"})
        html2 = generate_html(
            ctx2,
            app_package_name="test_pkg",
            dev_mode=False,
            prerender=True,
            app_version="0.0.0",
            wheel_filename="test.whl",
        )
        ctx2.dispose()

        assert "Page A" in html1
        assert "/a.css" in html1
        assert "Page A" not in html2
        assert "/a.css" not in html2
        assert "Page B" in html2
        assert "/b.css" in html2
        assert "Page B" not in html1
        assert "/b.css" not in html1

    def test_head_props_isolated(self):
        app = WebComPyApp(
            root_component=_IsolationRoot,
            config=WebComPyAppConfig(),
        )

        ctx1 = app.create_render_context()
        ctx1.set_head(
            {
                "title": "Isolated A",
                "meta": {"og:title": {"name": "og:title", "content": "A"}},
            }
        )
        ctx2 = app.create_render_context()
        ctx2.set_head(
            {
                "title": "Isolated B",
                "meta": {"og:title": {"name": "og:title", "content": "B"}},
            }
        )

        head1 = ctx1.head
        head2 = ctx2.head

        assert head1["title"].value == "Isolated A"
        assert head2["title"].value == "Isolated B"

        ctx1.dispose()
        ctx2.dispose()

    def test_concurrent_contexts(self):
        app = WebComPyApp(
            root_component=_IsolationRoot,
            config=WebComPyAppConfig(),
        )

        contexts = []
        for i in range(10):
            ctx = app.create_render_context(f"/page-{i}")
            ctx.set_title(f"Page {i}")
            contexts.append(ctx)

        for i, ctx in enumerate(contexts):
            assert ctx.head["title"].value == f"Page {i}"
            ctx.dispose()
