from __future__ import annotations

from typing import Any, TypedDict

from webcompy.components import ComponentContext, define_component, on_before_destroy
from webcompy.di import inject
from webcompy.elements import html, raw_html, repeat, switch
from webcompy.ports._keys import DOM_PORT_KEY, HOST_PORT_KEY
from webcompy.router import RouterLink, use_router
from webcompy.signal import Computed, Signal, use_computed
from webcompy.ui import Modal

from ..docs_manifest import DOCS_SECTIONS
from ..docs_search_index import DOCS_SEARCH_METADATA

_SEARCH_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" '
    'fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" '
    'stroke-linejoin="round" aria-hidden="true">'
    '<circle cx="11" cy="11" r="8"></circle>'
    '<path d="m21 21-4.3-4.3"></path>'
    "</svg>"
)

_CLOSE_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" '
    'fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" '
    'stroke-linejoin="round" aria-hidden="true">'
    '<path d="M18 6 6 18"></path>'
    '<path d="m6 6 12 12"></path>'
    "</svg>"
)


class SearchEntry(TypedDict):
    label: str
    section: str
    group: str
    path: str
    description: str
    headings_text: str
    haystack: str


def _build_search_index() -> tuple[SearchEntry, ...]:
    entries: list[SearchEntry] = []
    for section in DOCS_SECTIONS:
        section_title = section["title"]
        for page in section["pages"]:
            group = page.get("group", "")
            path = page["path"]
            meta_entry = DOCS_SEARCH_METADATA.get(path)
            description = meta_entry["description"] if meta_entry is not None else ""
            headings_text = " ".join(meta_entry["headings"]) if meta_entry is not None else ""
            slug_words = path.removeprefix("/documents/").replace("/", " ").replace("-", " ")
            haystack = " ".join((page["label"], section_title, group, slug_words, headings_text, description)).lower()
            entries.append(
                {
                    "label": page["label"],
                    "section": section_title,
                    "group": group,
                    "path": path,
                    "description": description,
                    "headings_text": headings_text,
                    "haystack": haystack,
                }
            )
    return tuple(entries)


_SEARCH_INDEX = _build_search_index()
_DEFAULT_RESULTS: list[SearchEntry] = list(_SEARCH_INDEX[:8])


def _filter_entries(raw_query: str) -> list[SearchEntry]:
    terms = [part for part in raw_query.strip().lower().split() if part]
    if not terms:
        return _DEFAULT_RESULTS
    scored: list[tuple[int, int, SearchEntry]] = []
    joined = " ".join(terms)
    for idx, entry in enumerate(_SEARCH_INDEX):
        haystack = entry["haystack"]
        if not all(term in haystack for term in terms):
            continue
        label_lower = entry["label"].lower()
        slug = entry["path"].removeprefix("/documents/").replace("/", " ").replace("-", " ")
        headings_slug = f"{entry['headings_text']} {slug}".lower()
        title_and_headings = f"{label_lower} {headings_slug}"
        desc_lower = entry["description"].lower()
        if label_lower.startswith(joined):
            rank = 0
        elif joined in label_lower:
            rank = 1
        elif all(term in label_lower for term in terms):
            rank = 2
        elif joined in headings_slug:
            rank = 3
        elif all(term in title_and_headings for term in terms):
            rank = 4
        elif joined in desc_lower:
            rank = 5
        else:
            rank = 6
        scored.append((rank, idx, entry))
    scored.sort(key=lambda item: (item[0], item[1]))
    return [item[2] for item in scored[:12]]


def _is_editable_element(element: Any) -> bool:
    if element is None:
        return False
    tag = str(getattr(element, "tagName", getattr(element, "nodeName", ""))).upper()
    if tag in {"INPUT", "TEXTAREA", "SELECT"}:
        return True
    return bool(getattr(element, "isContentEditable", False))


@define_component()
def DocsSearch(_: ComponentContext[None]):
    router = use_router()
    is_open: Signal[bool] = Signal(False)
    query: Signal[str] = Signal("")
    active_idx: Signal[int] = Signal(0)

    results = use_computed(lambda: _filter_entries(query.value))
    active_path = use_computed(
        lambda: results.value[min(active_idx.value, len(results.value) - 1)]["path"] if results.value else ""
    )
    has_results = use_computed(lambda: len(results.value) > 0)
    has_empty = use_computed(lambda: len(results.value) == 0)

    def _open(_ev: Any = None) -> None:
        query.value = ""
        active_idx.value = 0
        is_open.value = True

    def _close() -> None:
        is_open.value = False

    def _on_input(_ev: Any = None) -> None:
        active_idx.value = 0

    def _on_input_keydown(ev: Any) -> None:
        key = getattr(ev, "key", None)
        if key is None and isinstance(ev, dict):
            key = ev.get("key")
        matches = results.value
        if key == "ArrowDown":
            if matches:
                active_idx.value = (active_idx.value + 1) % len(matches)
            if hasattr(ev, "preventDefault"):
                ev.preventDefault()
        elif key == "ArrowUp":
            if matches:
                active_idx.value = (active_idx.value - 1) % len(matches)
            if hasattr(ev, "preventDefault"):
                ev.preventDefault()
        elif key == "Enter":
            if matches:
                target = matches[min(active_idx.value, len(matches) - 1)]
                _close()
                router.__set_path__(target["path"], None)
            if hasattr(ev, "preventDefault"):
                ev.preventDefault()

    host = inject(HOST_PORT_KEY, default=None)
    dom = inject(DOM_PORT_KEY, default=None)
    active_el_getter = (
        host.create_js_global_getter(
            "document",
            wrapper=lambda doc: getattr(doc, "activeElement", None) if doc is not None else None,
        )
        if host is not None
        else None
    )

    if dom is not None:

        def _on_global_keydown(ev: Any) -> None:
            key = getattr(ev, "key", None)
            if key is None and isinstance(ev, dict):
                key = ev.get("key")
            if not key:
                return
            ctrl = bool(getattr(ev, "ctrlKey", False))
            meta = bool(getattr(ev, "metaKey", False))
            if (ctrl or meta) and str(key).lower() == "k":
                if hasattr(ev, "preventDefault"):
                    ev.preventDefault()
                if is_open.value:
                    _close()
                else:
                    _open()
                return
            if key == "/" and not is_open.value:
                active_el = active_el_getter() if active_el_getter is not None else None
                target_el = getattr(ev, "target", None)
                if _is_editable_element(active_el) or _is_editable_element(target_el):
                    return
                if hasattr(ev, "preventDefault"):
                    ev.preventDefault()
                _open()

        remove_keydown = dom.add_document_event_listener("keydown", _on_global_keydown)

        @on_before_destroy
        def _cleanup_keydown() -> None:
            remove_keydown()

    def _render_result(entry: SearchEntry, _key: str | int = ""):
        path = entry["path"]
        meta = f"{entry['section']} / {entry['group']}" if entry["group"] else entry["section"]
        item_class = Computed(
            lambda: "docs-search-result active" if active_path.value == path else "docs-search-result"
        )
        main_children: list[Any] = [
            RouterLink(
                to=path,
                text=[entry["label"]],
                attrs={"class": "docs-search-result-link"},
                active_class="",
            ),
        ]
        if entry["description"]:
            main_children.append(html.SPAN({"class": "docs-search-result-desc"}, entry["description"]))
        return html.LI(
            {"class": item_class, "@click": lambda _ev: _close()},
            html.DIV({"class": "docs-search-result-main"}, *main_children),
            html.SPAN({"class": "docs-search-result-meta"}, meta),
        )

    def _render_modal_body():
        return html.DIV(
            {"class": "docs-search-body"},
            html.DIV(
                {"class": "docs-search-header"},
                html.INPUT(
                    {
                        "type": "search",
                        "id": "docs-search-input",
                        "class": "docs-search-input",
                        "placeholder": "Search documentation...",
                        "aria-label": "Search documentation",
                        ":bind": query,
                        "@input": _on_input,
                        "@keydown": _on_input_keydown,
                    }
                ),
                html.BUTTON(
                    {
                        "type": "button",
                        "class": "docs-search-close",
                        "aria-label": "Close search",
                        "@click": lambda _ev: _close(),
                    },
                    raw_html(_CLOSE_SVG, wrapper="span"),
                ),
            ),
            switch(
                {
                    "case": has_results,
                    "generator": lambda: html.UL(
                        {"class": "docs-search-results"},
                        repeat(results, _render_result, key=lambda item: item["path"]),
                    ),
                },
                {
                    "case": has_empty,
                    "generator": lambda: html.P(
                        {"class": "docs-search-empty"},
                        "No matching documentation pages found.",
                    ),
                },
            ),
        )

    return html.DIV(
        {"class": "docs-search-root"},
        html.BUTTON(
            {
                "type": "button",
                "class": "docs-search-trigger",
                "aria-label": "Search documentation",
                "aria-keyshortcuts": "Control+K Meta+K /",
                "@click": _open,
            },
            raw_html(_SEARCH_SVG, wrapper="span"),
            html.SPAN({"class": "docs-search-trigger-label"}, "Search"),
            html.KBD({"class": "docs-search-kbd"}, "/"),
        ),
        Modal(
            {
                "open": is_open,
                "on_close": _close,
                "aria_label": "Search documentation",
                "class_panel": "docs-search-panel",
            },
            slots={"default": _render_modal_body},
        ),
    )


DocsSearch.scoped_style = {
    ".docs-search-root": {
        "display": "inline-flex",
        "align-items": "center",
    },
    ".docs-search-trigger": {
        "display": "inline-flex",
        "align-items": "center",
        "gap": "var(--space-2)",
        "height": "2.25rem",
        "padding": "0 var(--space-3)",
        "font-family": "var(--font-sans)",
        "font-size": "var(--font-size-sm)",
        "font-weight": "500",
        "color": "var(--color-fg)",
        "background-color": "var(--color-bg-elevated)",
        "border": "1px solid var(--color-border)",
        "border-radius": "var(--radius-sm)",
        "cursor": "pointer",
        "transition": "border-color 0.15s ease, background-color 0.15s ease",
    },
    ".docs-search-trigger > span:first-child": {
        "display": "inline-flex",
        "align-items": "center",
    },
    ".docs-search-trigger:hover": {
        "border-color": "var(--color-link)",
        "background-color": "var(--color-bg-card)",
    },
    ".docs-search-trigger:focus-visible": {
        "outline": "2px solid var(--color-accent)",
        "outline-offset": "2px",
    },
    ".docs-search-kbd": {
        "padding": "0.05rem 0.35rem",
        "font-family": "var(--font-mono)",
        "font-size": "0.75rem",
        "color": "var(--color-fg-muted)",
        "background-color": "var(--color-bg)",
        "border": "1px solid var(--color-border)",
        "border-radius": "var(--radius-sm)",
        "line-height": "1.2",
    },
    "@media (max-width: 520px)": {
        ".docs-search-trigger-label": {
            "display": "none",
        },
        ".docs-search-kbd": {
            "display": "none",
        },
        ".docs-search-trigger": {
            "padding": "0 var(--space-2)",
        },
    },
}
