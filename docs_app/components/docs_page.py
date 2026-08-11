from webcompy.elements import html
from webcompy.template import MarkdownDocument


def _toc_href(current_path: str, heading_id: str) -> str:
    path = current_path if current_path.startswith("/") else "/" + current_path
    return f"{path}#{heading_id}"


def docs_page_template(doc: MarkdownDocument, current_path: str):
    children: list = [html.ARTICLE({"class": "prose"}, doc.content)]
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
