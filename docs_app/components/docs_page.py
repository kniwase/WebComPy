from typing import Any

from webcompy.elements import html
from webcompy.elements.types._element import Element
from webcompy.elements.types._fragment import FragmentElement
from webcompy.template import MarkdownDocument

from .demo_display import DemoComponentProps, DemoDisplay


def _toc_href(current_path: str, heading_id: str) -> str:
    path = current_path if current_path.startswith("/") else "/" + current_path
    return f"{path}#{heading_id}"


def _split_lead_and_body(content: Any) -> tuple[Any, Any | None]:
    if isinstance(content, FragmentElement):
        children = content._pending_children or content._children
        for index, child in enumerate(children):
            if isinstance(child, Element) and child._tag_name == "h2":
                if index == 0:
                    return content, None
                return FragmentElement(list(children[:index])), FragmentElement(list(children[index:]))
    return content, None


def _render_docs_page(doc: MarkdownDocument, current_path: str, article_children: list[Any]):
    children: list[Any] = [html.ARTICLE({"class": "prose"}, *article_children)]
    if doc.toc:
        children.append(
            html.ASIDE(
                {"class": "docs-toc"},
                html.NAV(
                    {"aria-label": "Table of contents"},
                    html.UL(
                        {"class": "docs-toc-list"},
                        *tuple(
                            html.LI(
                                {"class": f"docs-toc-level-{heading.level}"},
                                html.A({"href": _toc_href(current_path, heading.id)}, heading.text),
                            )
                            for heading in doc.toc
                        ),
                    ),
                ),
            )
        )
    return html.DIV({"class": "docs-page"}, *children)


def docs_page_template(doc: MarkdownDocument, current_path: str, extra_content: Any = None):
    article_children: list[Any] = [doc.content]
    if extra_content is not None:
        article_children.append(extra_content)
    return _render_docs_page(doc, current_path, article_children)


def examples_page_template(
    doc: MarkdownDocument,
    current_path: str,
    *,
    demo_app: str,
    demo_title: str | None = None,
    peer_demo: bool = False,
):
    lead, body = _split_lead_and_body(doc.content)
    normalized_path = current_path if current_path.startswith("/") else "/" + current_path
    props: DemoComponentProps = {
        "title": demo_title or str(doc.metadata.get("title", demo_app)),
        "app_name": demo_app,
        "demo_path": f"/_demos/{demo_app}/app.py",
    }
    if peer_demo:
        props["peer_demo"] = True
        props["new_tab_href"] = normalized_path
    article_children: list[Any] = [lead, DemoDisplay(props)]
    if body is not None:
        article_children.append(body)
    return _render_docs_page(doc, current_path, article_children)


DOCS_PAGE_SCOPED_STYLE = {
    " .docs-page": {
        "display": "grid",
        "grid-template-columns": "minmax(0, 1fr) 14rem",
        "gap": "var(--space-6)",
        "align-items": "start",
    },
    " .docs-toc": {
        "position": "sticky",
        "top": "var(--space-4)",
        "font-size": "var(--font-size-sm)",
    },
    " .docs-toc-list": {
        "list-style": "none",
        "margin": "0",
        "padding": "0",
        "border-left": "1px solid var(--color-border)",
    },
    " .docs-toc-list a": {
        "display": "block",
        "padding": "var(--space-1) var(--space-3)",
        "color": "var(--color-fg-muted)",
        "text-decoration": "none",
    },
    " .docs-toc-list a:hover": {
        "color": "var(--color-link)",
    },
    " .docs-toc-level-3": {
        "padding-left": "var(--space-3)",
    },
    " .docs-toc-level-4": {
        "padding-left": "var(--space-5)",
    },
    " .prose h1, .prose h2, .prose h3, .prose h4, .prose h5, .prose h6": {
        "scroll-margin-top": "5rem",
    },
    " @media (max-width: 1024px)": {
        " .docs-page": {
            "grid-template-columns": "minmax(0, 1fr)",
        },
        " .docs-toc": {
            "display": "none",
        },
    },
}
