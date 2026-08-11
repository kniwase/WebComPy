from __future__ import annotations

from pathlib import PurePosixPath
from typing import TypedDict

from webcompy.exception import WebComPyException
from webcompy.router import lazy

DOCS_ROOT = "/documents"


class DocsPageEntry(TypedDict, total=False):
    label: str
    path: str
    source: str
    component: str


class DocsSection(TypedDict):
    title: str
    pages: list[DocsPageEntry]


DOCS_INDEX: DocsPageEntry = {
    "label": "Documentation",
    "path": DOCS_ROOT,
    "component": "docs_app.pages.document.home:DocumentHomePage",
}


DOCS_SECTIONS: list[DocsSection] = [
    {
        "title": "Getting Started",
        "pages": [
            {
                "label": "Installation",
                "path": "/documents/getting-started/installation",
                "source": "documents/installation.md",
            },
            {
                "label": "Quickstart",
                "path": "/documents/getting-started/quickstart",
                "source": "documents/quickstart.md",
            },
        ],
    },
    {
        "title": "Guides",
        "pages": [
            {
                "label": "Signal Stream",
                "path": "/documents/signal-stream",
                "component": "docs_app.pages.document.signal_stream:SignalStreamPage",
            },
        ],
    },
]


def page_component_ref(entry: DocsPageEntry) -> str:
    if "component" in entry:
        return entry["component"]
    stem = PurePosixPath(entry["source"]).stem
    attr = "".join(part.capitalize() for part in stem.split("_")) + "Page"
    return f"docs_app.pages.document.{stem}:{attr}"


def validate_manifest(sections: list[DocsSection]) -> None:
    paths: set[str] = set()

    def _check_entry(entry: DocsPageEntry) -> None:
        has_source = "source" in entry
        has_component = "component" in entry
        if has_source == has_component:
            raise WebComPyException(f"Docs manifest entry must set exactly one of 'source'/'component': {entry!r}")
        if entry["path"] in paths:
            raise WebComPyException(f"Duplicate docs manifest path: {entry['path']!r}")
        paths.add(entry["path"])

    _check_entry(DOCS_INDEX)
    for section in sections:
        for entry in section["pages"]:
            _check_entry(entry)


def flatten_pages() -> list[DocsPageEntry]:
    return [page for section in DOCS_SECTIONS for page in section["pages"]]


def route_pages() -> list[DocsPageEntry]:
    return [DOCS_INDEX, *flatten_pages()]


def _route_path(path: str) -> str:
    if path == DOCS_ROOT:
        return ""
    return path.removeprefix(DOCS_ROOT + "/")


def route_children() -> list[dict]:
    return [
        {
            "path": _route_path(page["path"]),
            "component": lazy(page_component_ref(page), __file__),
        }
        for page in route_pages()
    ]


def _normalize(path: str) -> str:
    return "/" + path.strip("/")


def prev_next(path: str) -> tuple[DocsPageEntry | None, DocsPageEntry | None]:
    pages = flatten_pages()
    current = _normalize(path)
    for index, page in enumerate(pages):
        if _normalize(page["path"]) == current:
            prev_page = pages[index - 1] if index > 0 else None
            next_page = pages[index + 1] if index < len(pages) - 1 else None
            return prev_page, next_page
    return None, None


validate_manifest(DOCS_SECTIONS)
