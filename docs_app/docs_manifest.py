from __future__ import annotations

from pathlib import PurePosixPath
from typing import NotRequired, TypedDict

from webcompy.exception import WebComPyException
from webcompy.router import lazy

DOCS_ROOT = "/documents"


class DocsPageEntry(TypedDict):
    label: str
    path: str
    source: NotRequired[str]
    component: NotRequired[str]


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
                "label": "Signals and Streams",
                "path": "/documents/signal-stream",
                "source": "documents/signal_stream.md",
            },
            {
                "label": "Read-only Signals and Events",
                "path": "/documents/readonly-signal",
                "source": "documents/readonly_signal.md",
            },
            {
                "label": "Custom Elements",
                "path": "/documents/custom-elements",
                "source": "documents/custom_elements.md",
            },
            {
                "label": "Loading Screen",
                "path": "/documents/loading-screen",
                "source": "documents/loading_screen.md",
            },
            {
                "label": "Server-Sent Events",
                "path": "/documents/event-source",
                "source": "documents/event_source.md",
            },
            {
                "label": "WebSocket",
                "path": "/documents/websocket",
                "source": "documents/websocket.md",
            },
            {
                "label": "Typed Realtime",
                "path": "/documents/typed-realtime",
                "source": "documents/typed_realtime.md",
            },
            {
                "label": "RPC Contracts",
                "path": "/documents/rpc-contracts",
                "source": "documents/rpc_contracts.md",
            },
            {
                "label": "RPC",
                "path": "/documents/rpc",
                "source": "documents/rpc.md",
            },
            {
                "label": "RPC over WebSocket",
                "path": "/documents/rpc-websocket",
                "source": "documents/rpc_websocket.md",
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
        if "label" not in entry:
            raise WebComPyException(f"Docs manifest entry must include 'label': {entry!r}")
        if "path" not in entry:
            raise WebComPyException(f"Docs manifest entry must include 'path': {entry!r}")
        has_source = "source" in entry
        has_component = "component" in entry
        if has_source == has_component:
            raise WebComPyException(f"Docs manifest entry must set exactly one of 'source'/'component': {entry!r}")
        entry_path = entry["path"]
        if entry_path != DOCS_ROOT and not entry_path.startswith(DOCS_ROOT + "/"):
            raise WebComPyException(f"Docs manifest path must be under {DOCS_ROOT!r}: {entry!r}")
        if entry_path in paths:
            raise WebComPyException(f"Duplicate docs manifest path: {entry_path!r}")
        paths.add(entry_path)

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
