from __future__ import annotations

import asyncio

from webcompy.components._generator import define_component
from webcompy.testing import create_test_app


@define_component
def _IsolationRoot(context):
    from webcompy.elements import html

    return html.DIV({}, "content")


class TestRequestIsolation:
    def test_contexts_produce_independent_html(self):
        from webcompy.cli._html import generate_html

        app = create_test_app(root_component=_IsolationRoot)

        ctx1 = app.create_render_context("/page-a")
        ctx1.set_title("Page A")
        ctx1.append_link({"rel": "stylesheet", "href": "/a.css"})
        html1 = asyncio.run(
            generate_html(
                ctx1,
                app_package_name="test_pkg",
                dev_mode=False,
                prerender=True,
                app_version="0.0.0",
                wheel_filename="test.whl",
            )
        )
        ctx1.dispose()

        ctx2 = app.create_render_context("/page-b")
        ctx2.set_title("Page B")
        ctx2.append_link({"rel": "stylesheet", "href": "/b.css"})
        html2 = asyncio.run(
            generate_html(
                ctx2,
                app_package_name="test_pkg",
                dev_mode=False,
                prerender=True,
                app_version="0.0.0",
                wheel_filename="test.whl",
            )
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
        app = create_test_app(root_component=_IsolationRoot)

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
        app = create_test_app(root_component=_IsolationRoot)

        contexts = []
        for i in range(10):
            ctx = app.create_render_context(f"/page-{i}")
            ctx.set_title(f"Page {i}")
            contexts.append(ctx)

        for i, ctx in enumerate(contexts):
            assert ctx.head["title"].value == f"Page {i}"
            ctx.dispose()

    def test_app_proxy_properties_not_corrupted_by_concurrent_contexts(self):
        app = create_test_app(root_component=_IsolationRoot)

        async def _with_context(path, lang):
            ctx = app.create_render_context(path)
            try:
                app.set_html_attr("lang", lang)
                app.set_title(f"Title {lang}")
                assert app.html_attrs["lang"] == lang
                assert ctx.head["title"].value == f"Title {lang}"
                return lang
            finally:
                ctx.dispose()

        async def _main():
            results = await asyncio.gather(
                _with_context("/ja", "ja"),
                _with_context("/en", "en"),
                _with_context("/fr", "fr"),
            )
            assert set(results) == {"ja", "en", "fr"}

        asyncio.run(_main())

    def test_create_render_context_not_corrupted_by_sequential_dispose(self):
        app = create_test_app(root_component=_IsolationRoot)

        ctx1 = app.create_render_context()
        app.set_html_attr("lang", "ja")
        ctx1.dispose()

        ctx2 = app.create_render_context()
        app.set_html_attr("lang", "en")
        assert app.html_attrs["lang"] == "en"
        ctx2.dispose()

        ctx3 = app.create_render_context()
        assert app.html_attrs == {}
        ctx3.dispose()
