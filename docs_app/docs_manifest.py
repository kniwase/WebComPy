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


CATEGORY_SECTIONS: dict[str, str] = {
    "Getting Started": f"{DOCS_ROOT}/getting-started",
    "Guides": f"{DOCS_ROOT}/guides",
    "Basic Usage": f"{DOCS_ROOT}/basic",
    "Advanced Usage": f"{DOCS_ROOT}/advanced",
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
        "title": "Basic Usage",
        "pages": [
            {
                "label": "UI Primitives",
                "path": "/documents/basic/ui-primitives",
                "component": "docs_app.pages.document.ui_primitives:UiPrimitivesPage",
            },
            {
                "label": "Overlay Components",
                "path": "/documents/basic/overlay",
                "component": "docs_app.pages.document.overlay:OverlayPage",
            },
            {
                "label": "Disclosure & Feedback",
                "path": "/documents/basic/disclosure",
                "component": "docs_app.pages.document.disclosure:DisclosurePage",
            },
        ],
    },
    {
        "title": "Advanced Usage",
        "pages": [
            {
                "label": "Custom Elements",
                "path": "/documents/advanced/custom-elements",
                "source": "documents/custom_elements.md",
            },
            {
                "label": "Signals and Streams",
                "path": "/documents/advanced/signal-stream",
                "source": "documents/signal_stream.md",
            },
            {
                "label": "Read-only Signals and Events",
                "path": "/documents/advanced/readonly-signal",
                "source": "documents/readonly_signal.md",
            },
            {
                "label": "Internationalization",
                "path": "/documents/advanced/i18n",
                "source": "documents/i18n.md",
            },
            {
                "label": "Loading Screen",
                "path": "/documents/advanced/loading-screen",
                "source": "documents/loading_screen.md",
            },
            {
                "label": "Server-Sent Events",
                "path": "/documents/advanced/event-source",
                "source": "documents/event_source.md",
            },
            {
                "label": "WebSocket",
                "path": "/documents/advanced/websocket",
                "source": "documents/websocket.md",
            },
            {
                "label": "Typed Realtime",
                "path": "/documents/advanced/typed-realtime",
                "source": "documents/typed_realtime.md",
            },
            {
                "label": "RPC",
                "path": "/documents/advanced/rpc",
                "source": "documents/rpc.md",
            },
            {
                "label": "RPC Contracts",
                "path": "/documents/advanced/rpc-contracts",
                "source": "documents/rpc_contracts.md",
            },
            {
                "label": "RPC over WebSocket",
                "path": "/documents/advanced/rpc-websocket",
                "source": "documents/rpc_websocket.md",
            },
            {
                "label": "Progressive Web App",
                "path": "/documents/advanced/pwa",
                "source": "documents/pwa.md",
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

    def _check_entry(entry: DocsPageEntry, category_prefix: str | None = None) -> None:
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
        if category_prefix is not None and not entry_path.startswith(category_prefix + "/"):
            raise WebComPyException(
                f"Docs manifest path must start with the category prefix {category_prefix!r}: {entry!r}"
            )

    _check_entry(DOCS_INDEX)
    seen_index = -1
    for section in sections:
        title = section["title"]
        if title not in CATEGORY_SECTIONS:
            raise WebComPyException(f"Unknown docs section title: {title!r}")
        index = list(CATEGORY_SECTIONS).index(title)
        if index <= seen_index:
            raise WebComPyException(f"Docs sections must follow the category order: {title!r}")
        seen_index = index
        for entry in section["pages"]:
            _check_entry(entry, CATEGORY_SECTIONS[title])


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
