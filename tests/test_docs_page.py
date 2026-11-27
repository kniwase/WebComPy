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


class TestHeadingAnchorsAndTemplatePlacement:
    def test_docs_page_template_normalizes_heading_anchor_hrefs(self) -> None:
        from docs_app.components.docs_page import docs_page_template
        from webcompy.components import ComponentContext, define_component
        from webcompy.elements import html
        from webcompy.elements.types._fragment import FragmentElement
        from webcompy.template import HeadingInfo, MarkdownDocument
        from webcompy_testing import TestRenderer

        content = FragmentElement(
            [
                html.H1({"id": "title"}, "Title"),
                html.H2(
                    {"id": "sub-heading"},
                    "Sub Heading",
                    html.A({"class": "heading-anchor", "href": "#sub-heading"}, "#"),
                ),
            ]
        )
        doc = MarkdownDocument(
            content=content,
            metadata={"title": "Title"},
            toc=(
                HeadingInfo(level=1, text="Title", id="title"),
                HeadingInfo(level=2, text="Sub Heading", id="sub-heading"),
            ),
        )

        @define_component()
        def AnchoredHost(_: ComponentContext[None]):
            return docs_page_template(doc, "/documents/basic/components/")

        with TestRenderer.render(AnchoredHost) as result:
            rendered = result.to_html()
            assert 'href="/documents/basic/components/#sub-heading"' in rendered

    def test_docs_page_template_before_heading_id_places_extra_before_notes_and_next_steps(self) -> None:
        from docs_app.components.docs_page import docs_page_template
        from webcompy.components import ComponentContext, define_component
        from webcompy.elements import html
        from webcompy.elements.types._fragment import FragmentElement
        from webcompy.template import HeadingInfo, MarkdownDocument
        from webcompy_testing import TestRenderer

        content = FragmentElement(
            [
                html.H1({"id": "overlay"}, "Overlay"),
                html.H2({"id": "live-example"}, "Live example"),
                html.H2({"id": "notes--caveats"}, "Notes & caveats"),
                html.H2({"id": "next-steps"}, "Next steps"),
            ]
        )
        doc = MarkdownDocument(
            content=content,
            metadata={"title": "Overlay"},
            toc=(
                HeadingInfo(level=1, text="Overlay", id="overlay"),
                HeadingInfo(level=2, text="Live example", id="live-example"),
                HeadingInfo(level=2, text="Notes & caveats", id="notes--caveats"),
                HeadingInfo(level=2, text="Next steps", id="next-steps"),
            ),
        )

        @define_component()
        def OrderedHost(_: ComponentContext[None]):
            return docs_page_template(
                doc,
                "/documents/basic/overlay",
                extra_content=html.DIV({"class": "overlay-demo"}, "Demo body"),
                before_heading_id="notes--caveats",
            )

        with TestRenderer.render(OrderedHost) as result:
            rendered = result.to_html()
            assert rendered.index("Live example") < rendered.index("Demo body")
            assert rendered.index("Demo body") < rendered.index("Notes &amp; caveats")
            assert rendered.index("Notes &amp; caveats") < rendered.index("Next steps")

    def test_docs_page_components_do_not_duplicate_docs_page_style(self) -> None:
        from docs_app.pages.document.installation import InstallationPage
        from docs_app.pages.document.overlay import OverlayPage
        from docs_app.pages.document.ui_primitives import UiPrimitivesPage

        assert InstallationPage.scoped_style == ""
        assert UiPrimitivesPage.scoped_style == ""
        assert OverlayPage.scoped_style == ""


class TestDocsSearch:
    def test_search_filters_descriptions_and_headings(self) -> None:
        from docs_app.components.docs_search import _filter_entries

        assert any(entry["path"] == "/documents/basic/routing" for entry in _filter_entries("router"))
        assert any(entry["path"] == "/documents/basic/overlay" for entry in _filter_entries("modal"))
        assert any(entry["path"] == "/documents/basic/disclosure" for entry in _filter_entries("tabs"))
        assert any(entry["path"] == "/documents/api/reactivity" for entry in _filter_entries("use_state"))
        assert len(_filter_entries("signal")) > 2

    def test_search_index_module_matches_generator(self) -> None:
        import scripts.generate_docs_search_index as gen

        assert gen.main(["--check"]) == 0

    def test_search_close_button_uses_svg_icon(self, monkeypatch) -> None:
        import webcompy.elements.types._teleport as _tp
        from docs_app.components.docs_search import DocsSearch
        from webcompy.di import DIScope
        from webcompy.di._keys import _ROUTER_KEY
        from webcompy.ports._keys import ASYNC_SCHEDULER_PORT_KEY, HISTORY_PORT_KEY
        from webcompy.router import Router, RouterKey
        from webcompy_server.ports._dom import ServerDOMPort
        from webcompy_server.ports._virtual_dom import VirtualDOMEvent
        from webcompy_testing import FakeHistoryPort, TestRenderer, run_sync

        monkeypatch.setattr(_tp, "ENVIRONMENT", "pyscript")
        history = FakeHistoryPort()
        scope = DIScope()
        router = Router(history=history)
        scope.provide(HISTORY_PORT_KEY, history)
        scope.provide(RouterKey, router)
        scope.provide(_ROUTER_KEY, router)

        with TestRenderer.render(DocsSearch, parent_scope=scope) as res:
            trigger = res.query_selector("button")
            assert trigger is not None
            trigger.dispatchEvent(VirtualDOMEvent("click"))
            run_sync(res._scope.inject(ASYNC_SCHEDULER_PORT_KEY).drain())
            body_html = ServerDOMPort().render_html(res.body_node)
            assert 'class="docs-search-close"' in body_html
            assert 'aria-label="Close search"' in body_html
            assert "<svg" in body_html
            assert ">Esc<" not in body_html
