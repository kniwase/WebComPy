from __future__ import annotations

from docs_app.components.docs_page import _toc_href, examples_page_template


class TestTocHref:
    def test_preserves_trailing_slash(self) -> None:
        href = _toc_href("/documents/getting-started/installation/", "install-with-uv-recommended")
        assert href == "/documents/getting-started/installation/#install-with-uv-recommended"

    def test_without_trailing_slash(self) -> None:
        href = _toc_href("/documents/getting-started/installation", "install-with-uv-recommended")
        assert href == "/documents/getting-started/installation#install-with-uv-recommended"

    def test_relative_current_path_normalized(self) -> None:
        href = _toc_href("documents/getting-started/installation", "intro")
        assert href == "/documents/getting-started/installation#intro"

    def test_root_path(self) -> None:
        assert _toc_href("/", "intro") == "/#intro"


class TestExamplesPageTemplate:
    def _sample_doc(self):
        from webcompy.elements import html
        from webcompy.elements.types._fragment import FragmentElement
        from webcompy.template import HeadingInfo, MarkdownDocument

        content = FragmentElement(
            [
                html.H1({"id": "hello-world"}, "Hello World"),
                html.P({}, "Short lead sentence."),
                html.H2({"id": "what-this-demonstrates"}, "What this demonstrates"),
                html.P({}, "Explanation body."),
            ]
        )
        return MarkdownDocument(
            content=content,
            metadata={"title": "Hello World", "description": "desc"},
            toc=(
                HeadingInfo(level=1, text="Hello World", id="hello-world"),
                HeadingInfo(level=2, text="What this demonstrates", id="what-this-demonstrates"),
            ),
        )

    def test_inserts_demo_between_lead_and_first_h2(self) -> None:
        from webcompy.components import ComponentContext, define_component
        from webcompy_testing import TestRenderer

        doc = self._sample_doc()

        @define_component()
        def ExampleHost(_: ComponentContext[None]):
            return examples_page_template(doc, "/documents/examples/hello-world", demo_app="helloworld")

        with TestRenderer.render(ExampleHost) as result:
            rendered = result.to_html()
            assert "Short lead sentence." in rendered
            assert "demo-display" in rendered
            assert "What this demonstrates" in rendered
            assert rendered.index("Short lead sentence.") < rendered.index("demo-display")
            assert rendered.index("demo-display") < rendered.index("What this demonstrates")
            assert '/documents/examples/hello-world#what-this-demonstrates"' in rendered
            iframe = result.query_selector("iframe")
            assert iframe is not None
            assert "demo-iframe" in (iframe.getAttribute("class") or "").split()
            assert iframe.getAttribute("data-demo-auto-resize") == "true"

    def test_peer_demo_renders_two_iframes_and_new_tab_link(self) -> None:
        from webcompy.components import ComponentContext, define_component
        from webcompy_testing import TestRenderer

        doc = self._sample_doc()

        @define_component()
        def PeerExampleHost(_: ComponentContext[None]):
            return examples_page_template(
                doc,
                "/documents/examples/storage-sync",
                demo_app="storage_sync",
                demo_title="Storage Sync",
                peer_demo=True,
            )

        with TestRenderer.render(PeerExampleHost) as result:
            rendered = result.to_html()
            iframes = result.query_selector_all("iframe")
            assert len(iframes) == 2
            assert [frame.getAttribute("title") for frame in iframes] == ["Window A", "Window B"]
            assert 'href="/documents/examples/storage-sync"' in rendered
            assert "Open demo in new tab" in rendered
