from typing import Any

from webcompy.app import WebComPyApp
from webcompy.components import ComponentContext, define_component
from webcompy.elements import html
from webcompy.signal import use_computed, use_state
from webcompy.storage import use_local_storage

STORAGE_KEY = "webcompy-docs-storage-sync"


def _default_payload() -> dict[str, Any]:
    return {
        "theme": "ocean",
        "note": "Shared across tabs",
        "count": 0,
    }


@define_component()
def StorageSyncDemo(_: ComponentContext[None]):
    shared = use_local_storage(STORAGE_KEY, _default_payload, sync_tabs=True)
    note_draft = use_state(lambda: "")

    def _set_theme(name: str):
        def _on_click(_ev: Any) -> None:
            current = dict(shared.value)
            current["theme"] = name
            shared.value = current

        return _on_click

    def _increment(_ev: Any) -> None:
        current = dict(shared.value)
        current["count"] = int(current.get("count", 0)) + 1
        shared.value = current

    def _save_note(_ev: Any) -> None:
        text = note_draft.value.strip()
        if not text:
            return
        current = dict(shared.value)
        current["note"] = text
        shared.value = current
        note_draft.value = ""

    def _reset(_ev: Any) -> None:
        shared.value = _default_payload()
        note_draft.value = ""

    return html.DIV(
        {
            "class": use_computed(lambda: f"storage-sync-demo theme-{shared.value.get('theme', 'ocean')}"),
        },
        html.H1({}, "Cross-Tab Storage Sync"),
        html.DIV(
            {"class": "status-card"},
            html.P({"class": "status-theme"}, use_computed(lambda: f"Theme: {shared.value.get('theme', 'ocean')}")),
            html.P(
                {"class": "status-note"},
                use_computed(lambda: f"Note: {shared.value.get('note', 'Shared across tabs')}"),
            ),
            html.P({"class": "status-count"}, use_computed(lambda: f"Count: {shared.value.get('count', 0)}")),
        ),
        html.DIV(
            {"class": "control-row"},
            html.BUTTON({"type": "button", "@click": _set_theme("ocean")}, "Ocean"),
            html.BUTTON({"type": "button", "@click": _set_theme("forest")}, "Forest"),
            html.BUTTON({"type": "button", "@click": _set_theme("sunset")}, "Sunset"),
        ),
        html.DIV(
            {"class": "note-row"},
            html.INPUT(
                {
                    "type": "text",
                    "placeholder": "Type a note to sync...",
                    ":bind": note_draft,
                }
            ),
            html.BUTTON({"type": "button", "@click": _save_note}, "Save Note"),
        ),
        html.DIV(
            {"class": "control-row"},
            html.BUTTON({"type": "button", "@click": _increment}, "+1 Counter"),
            html.BUTTON({"type": "button", "@click": _reset}, "Reset"),
        ),
    )


StorageSyncDemo.scoped_style = {
    ".storage-sync-demo": {
        "font-family": "var(--font-sans, sans-serif)",
        "padding": "var(--space-3)",
        "border-radius": "var(--radius-sm)",
        "border": "2px solid var(--color-border)",
        "background": "var(--color-bg-card)",
        "color": "var(--color-fg)",
    },
    ".storage-sync-demo.theme-ocean": {
        "border-color": "var(--color-accent)",
        "background": "color-mix(in srgb, var(--color-accent) 12%, var(--color-bg-card))",
        "color": "var(--color-fg)",
    },
    ".storage-sync-demo.theme-forest": {
        "border-color": "var(--color-success)",
        "background": "color-mix(in srgb, var(--color-success) 12%, var(--color-bg-card))",
        "color": "var(--color-fg)",
    },
    ".storage-sync-demo.theme-sunset": {
        "border-color": "var(--color-warning)",
        "background": "color-mix(in srgb, var(--color-warning) 14%, var(--color-bg-card))",
        "color": "var(--color-fg)",
    },
    ".storage-sync-demo h1": {
        "margin": "0 0 var(--space-2) 0",
        "font-size": "var(--font-size-lg, 1.125rem)",
    },
    ".status-card": {
        "padding": "var(--space-2) var(--space-3)",
        "border": "1px solid var(--color-border)",
        "border-radius": "var(--radius-sm)",
        "background": "var(--color-bg)",
        "color": "var(--color-fg)",
        "margin-bottom": "var(--space-3)",
    },
    ".status-card p": {
        "margin": "0.25rem 0",
        "font-weight": "500",
    },
    ".control-row, .note-row": {
        "display": "flex",
        "flex-wrap": "wrap",
        "gap": "var(--space-2)",
        "margin-top": "var(--space-2)",
    },
    ".note-row input": {
        "flex": "1",
        "min-width": "10rem",
        "padding": "0.35rem 0.5rem",
        "border": "1px solid var(--color-border)",
        "border-radius": "var(--radius-sm)",
        "background": "var(--color-bg)",
        "color": "var(--color-fg)",
    },
    ".storage-sync-demo button": {
        "padding": "0.35rem 0.75rem",
        "border": "1px solid var(--color-border)",
        "border-radius": "var(--radius-sm)",
        "background": "var(--color-bg-elevated)",
        "color": "var(--color-fg)",
        "cursor": "pointer",
    },
}

app = WebComPyApp(root_component=StorageSyncDemo)
app.run()
