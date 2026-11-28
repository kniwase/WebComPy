from typing import Any

from webcompy.elements import html
from webcompy.elements.types._element import Element
from webcompy.elements.types._fragment import FragmentElement
from webcompy.template import MarkdownDocument

from .demo_display import DemoComponentProps, DemoDisplay


def _toc_href(current_path: str, heading_id: str) -> str:
    path = current_path if current_path.startswith("/") else "/" + current_path
    return f"{path}#{heading_id}"


def _normalize_heading_anchors(node: Any, current_path: str) -> None:
    if isinstance(node, Element) and node._tag_name == "a":
        raw_class = node._attrs.get("class")
        if isinstance(raw_class, str) and "heading-anchor" in raw_class.split():
            href = node._attrs.get("href")
            if isinstance(href, str) and href.startswith("#"):
                node._attrs["href"] = _toc_href(current_path, href[1:])
            return
    for lst in (getattr(node, "_children", None), getattr(node, "_pending_children", None)):
        if isinstance(lst, list):
            for child in lst:
                _normalize_heading_anchors(child, current_path)


def _split_lead_and_body(content: Any) -> tuple[Any, Any | None]:
    if isinstance(content, FragmentElement):
        children = content._pending_children or content._children
        for index, child in enumerate(children):
            if isinstance(child, Element) and child._tag_name == "h2":
                if index == 0:
                    return content, None
                return FragmentElement(list(children[:index])), FragmentElement(list(children[index:]))
    return content, None


def _split_before_heading_id(content: Any, heading_id: str) -> tuple[Any | None, Any | None]:
    if isinstance(content, FragmentElement):
        children = content._pending_children or content._children
        for index, child in enumerate(children):
            if isinstance(child, Element) and child._attrs.get("id") == heading_id:
                if index == 0:
                    return None, content
                return FragmentElement(list(children[:index])), FragmentElement(list(children[index:]))
    return content, None


def _render_docs_page(doc: MarkdownDocument, current_path: str, article_children: list[Any]):
    for child in article_children:
        _normalize_heading_anchors(child, current_path)
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


def docs_page_template(
    doc: MarkdownDocument,
    current_path: str,
    extra_content: Any = None,
    *,
    before_heading_id: str | None = None,
):
    if extra_content is not None and before_heading_id is not None:
        head, tail = _split_before_heading_id(doc.content, before_heading_id)
        article_children: list[Any] = []
        if head is not None:
            article_children.append(head)
        article_children.append(extra_content)
        if tail is not None:
            article_children.append(tail)
        return _render_docs_page(doc, current_path, article_children)
    article_children = [doc.content]
    if extra_content is not None:
        article_children.append(extra_content)
    return _render_docs_page(doc, current_path, article_children)


def docs_page_template_with_demo(
    doc: MarkdownDocument,
    current_path: str,
    *,
    demo_app: str,
    demo_title: str | None = None,
    before_heading_id: str,
):
    head, tail = _split_before_heading_id(doc.content, before_heading_id)
    props: DemoComponentProps = {
        "title": demo_title or str(doc.metadata.get("title", demo_app)),
        "app_name": demo_app,
        "demo_path": f"/_demos/{demo_app}/app.py",
    }
    article_children: list[Any] = []
    if head is not None:
        article_children.append(head)
    article_children.append(DemoDisplay(props))
    if tail is not None:
        article_children.append(tail)
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
