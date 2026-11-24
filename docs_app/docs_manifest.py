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
    group: NotRequired[str]


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
                "label": "What is WebComPy",
                "path": "/documents/getting-started/what-is-webcompy",
                "source": "documents/what_is_webcompy.md",
            },
            {
                "label": "Why WebComPy",
                "path": "/documents/getting-started/why-webcompy",
                "source": "documents/why_webcompy.md",
            },
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
            {
                "label": "Project Structure",
                "path": "/documents/getting-started/project-structure",
                "source": "documents/project_structure.md",
            },
        ],
    },
    {
        "title": "Guides",
        "pages": [
            {
                "label": "Overview",
                "path": "/documents/guides/overview",
                "source": "documents/guides_overview.md",
            },
            {
                "label": "Step 1: App Shell",
                "path": "/documents/guides/todo-app-shell",
                "source": "documents/guides_step1_state.md",
            },
            {
                "label": "Step 2: Components",
                "path": "/documents/guides/todo-components",
                "source": "documents/guides_step2_components.md",
            },
            {
                "label": "Step 3: Navigation",
                "path": "/documents/guides/todo-navigation",
                "source": "documents/guides_step3_navigation.md",
            },
            {
                "label": "Step 4: Forms",
                "path": "/documents/guides/todo-forms",
                "source": "documents/guides_step4_forms.md",
            },
            {
                "label": "Step 5: Remote Data",
                "path": "/documents/guides/todo-remote-data",
                "source": "documents/guides_step5_remote_data.md",
            },
            {
                "label": "Step 6: Deploy",
                "path": "/documents/guides/todo-deploy",
                "source": "documents/guides_step6_deploy.md",
            },
        ],
    },
    {
        "title": "Basic Usage",
        "pages": [
            {
                "label": "Components",
                "path": "/documents/basic/components",
                "source": "documents/basic_components.md",
            },
            {
                "label": "HTML Templates",
                "path": "/documents/basic/template-html",
                "source": "documents/basic_template_html.md",
            },
            {
                "label": "Reactive State",
                "path": "/documents/basic/reactive-state",
                "source": "documents/basic_reactive_state.md",
            },
            {
                "label": "Elements & Events",
                "path": "/documents/basic/elements-and-events",
                "source": "documents/basic_elements_events.md",
            },
            {
                "label": "Markdown Documents",
                "path": "/documents/basic/markdown-documents",
                "source": "documents/basic_markdown_documents.md",
            },
            {
                "label": "Routing",
                "path": "/documents/basic/routing",
                "source": "documents/basic_routing.md",
            },
            {
                "label": "Forms",
                "path": "/documents/basic/forms",
                "source": "documents/basic_forms.md",
            },
            {
                "label": "HTTP & Async",
                "path": "/documents/basic/http-and-async",
                "source": "documents/basic_http_async.md",
            },
            {
                "label": "Styling & Themes",
                "path": "/documents/basic/styling-and-themes",
                "source": "documents/basic_styling.md",
            },
            {
                "label": "Storage",
                "path": "/documents/basic/storage",
                "source": "documents/basic_storage.md",
            },
            {
                "label": "Error Handling",
                "path": "/documents/basic/error-handling",
                "source": "documents/basic_error_handling.md",
            },
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
                "label": "Read-only Signals and Events",
                "path": "/documents/advanced/readonly-signal",
                "source": "documents/readonly_signal.md",
                "group": "Realtime & RPC",
            },
            {
                "label": "Signals and Streams",
                "path": "/documents/advanced/signal-stream",
                "source": "documents/signal_stream.md",
                "group": "Realtime & RPC",
            },
            {
                "label": "Server-Sent Events",
                "path": "/documents/advanced/event-source",
                "source": "documents/event_source.md",
                "group": "Realtime & RPC",
            },
            {
                "label": "WebSocket",
                "path": "/documents/advanced/websocket",
                "source": "documents/websocket.md",
                "group": "Realtime & RPC",
            },
            {
                "label": "Typed Realtime",
                "path": "/documents/advanced/typed-realtime",
                "source": "documents/typed_realtime.md",
                "group": "Realtime & RPC",
            },
            {
                "label": "RPC Contracts",
                "path": "/documents/advanced/rpc-contracts",
                "source": "documents/rpc_contracts.md",
                "group": "Realtime & RPC",
            },
            {
                "label": "RPC",
                "path": "/documents/advanced/rpc",
                "source": "documents/rpc.md",
                "group": "Realtime & RPC",
            },
            {
                "label": "RPC over WebSocket",
                "path": "/documents/advanced/rpc-websocket",
                "source": "documents/rpc_websocket.md",
                "group": "Realtime & RPC",
            },
            {
                "label": "RPC Streaming",
                "path": "/documents/advanced/rpc-streaming",
                "source": "documents/rpc_streaming.md",
                "group": "Realtime & RPC",
            },
            {
                "label": "SSR & SSG",
                "path": "/documents/advanced/ssr-and-ssg",
                "source": "documents/ssr_ssg.md",
                "group": "Rendering & Performance",
            },
            {
                "label": "Hydration & Data Transfer",
                "path": "/documents/advanced/hydration-and-transfer",
                "source": "documents/hydration_and_transfer.md",
                "group": "Rendering & Performance",
            },
            {
                "label": "Async Rendering & Boundaries",
                "path": "/documents/advanced/async-rendering-and-boundaries",
                "source": "documents/async_rendering_boundaries.md",
                "group": "Rendering & Performance",
            },
            {
                "label": "Transition",
                "path": "/documents/advanced/transition",
                "source": "documents/transition.md",
                "group": "Rendering & Performance",
            },
            {
                "label": "Teleport",
                "path": "/documents/advanced/teleport",
                "source": "documents/teleport.md",
                "group": "Rendering & Performance",
            },
            {
                "label": "Loading Screen",
                "path": "/documents/advanced/loading-screen",
                "source": "documents/loading_screen.md",
                "group": "Rendering & Performance",
            },
            {
                "label": "Styling Deep Dive",
                "path": "/documents/advanced/styling-deep-dive",
                "source": "documents/styling_deep_dive.md",
                "group": "Rendering & Performance",
            },
            {
                "label": "Progressive Web App",
                "path": "/documents/advanced/pwa",
                "source": "documents/pwa.md",
                "group": "Rendering & Performance",
            },
            {
                "label": "Dependency Injection Deep Dive",
                "path": "/documents/advanced/dependency-injection-deep-dive",
                "source": "documents/dependency_injection_deep_dive.md",
                "group": "Architecture & Integration",
            },
            {
                "label": "Middleware",
                "path": "/documents/advanced/middleware",
                "source": "documents/middleware.md",
                "group": "Architecture & Integration",
            },
            {
                "label": "Routing Deep Dive",
                "path": "/documents/advanced/routing-deep-dive",
                "source": "documents/routing_deep_dive.md",
                "group": "Architecture & Integration",
            },
            {
                "label": "Plugins",
                "path": "/documents/advanced/plugins",
                "source": "documents/plugins.md",
                "group": "Architecture & Integration",
            },
            {
                "label": "Typed API Deep Dive",
                "path": "/documents/advanced/typed-api-deep-dive",
                "source": "documents/typed_api_deep_dive.md",
                "group": "Architecture & Integration",
            },
            {
                "label": "UI Headless Contract",
                "path": "/documents/advanced/ui-headless-contract",
                "source": "documents/ui_headless_contract.md",
                "group": "Architecture & Integration",
            },
            {
                "label": "Custom Elements",
                "path": "/documents/advanced/custom-elements",
                "source": "documents/custom_elements.md",
                "group": "Architecture & Integration",
            },
            {
                "label": "Persistence Patterns",
                "path": "/documents/advanced/persistence-patterns",
                "source": "documents/persistence_patterns.md",
                "group": "Architecture & Integration",
            },
            {
                "label": "Internationalization",
                "path": "/documents/advanced/i18n",
                "source": "documents/i18n.md",
                "group": "Architecture & Integration",
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
        if "group" in entry:
            group = entry["group"]
            if not isinstance(group, str) or not group.strip():
                raise WebComPyException(f"Docs manifest entry 'group' must be a non-empty string: {entry!r}")

    _check_entry(DOCS_INDEX)
    seen_index = -1
    for section in sections:
        if "title" not in section:
            raise WebComPyException(f"Docs manifest section must include 'title': {section!r}")
        title = section["title"]
        if title not in CATEGORY_SECTIONS:
            raise WebComPyException(f"Unknown docs section title: {title!r}")
        index = list(CATEGORY_SECTIONS).index(title)
        if index <= seen_index:
            raise WebComPyException(f"Docs sections must follow the category order: {title!r}")
        seen_index = index
        if not section["pages"]:
            raise WebComPyException(f"Docs section must include at least one page: {title!r}")
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
