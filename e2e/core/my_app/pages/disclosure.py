"""Disclosure components E2E page."""

from webcompy.components import ComponentContext, define_component
from webcompy.elements import html
from webcompy.signal import use_state
from webcompy.ui import Accordion, Alert, Badge, Card, Collapse, Progress, Tabs


@define_component()
def DisclosurePage(context: ComponentContext[None]):
    """E2E page for disclosure and feedback components."""

    context.set_title("Disclosure - E2E")
    active_tab = use_state(lambda: "a")
    collapse_open = use_state(lambda: False)
    progress_value = use_state(lambda: 20)

    def _on_select(key: str) -> None:
        active_tab.value = key

    def _on_collapse_toggle(is_open: bool) -> None:
        collapse_open.value = is_open

    def _bump(_event) -> None:
        progress_value.value = min(100.0, float(progress_value.value) + 20)

    tabs = [
        {
            "key": "a",
            "label": "Alpha",
            "content": lambda: html.DIV(
                {"data-testid": "panel-a"},
                html.INPUT({"data-testid": "tab-input-a", "type": "text", "placeholder": "type here"}),
            ),
        },
        {
            "key": "b",
            "label": "Beta",
            "content": lambda: html.SPAN({"data-testid": "panel-b"}, "Beta panel"),
        },
        {
            "key": "c",
            "label": "Gamma",
            "content": lambda: html.SPAN({"data-testid": "panel-c"}, "Gamma panel"),
        },
    ]

    items = [
        {"key": "i1", "label": "First", "content": lambda: html.P({"data-testid": "acc-body-1"}, "First body")},
        {"key": "i2", "label": "Second", "content": lambda: html.P({"data-testid": "acc-body-2"}, "Second body")},
    ]

    return html.DIV(
        {"data-testid": "disclosure-page"},
        html.H2({}, "Tabs"),
        Tabs({"tabs": tabs, "active": active_tab, "on_select": _on_select, "aria_label": "Demo tabs"}),
        html.H2({}, "Collapse"),
        Collapse(
            {"open": collapse_open, "on_toggle": _on_collapse_toggle},
            slots={
                "trigger": lambda: html.SPAN({"data-testid": "collapse-trigger-label"}, "Toggle details"),
                "default": lambda: html.P({"data-testid": "collapse-body"}, "Collapsed body text"),
            },
        ),
        html.H2({}, "Accordion"),
        Accordion({"items": items, "single_open": True}),
        html.H2({}, "Alert"),
        Alert(
            {"variant": "error", "dismissable": True},
            slots={"default": lambda: html.SPAN({"data-testid": "alert-message"}, "Something failed")},
        ),
        html.H2({}, "Progress"),
        Progress({"value": progress_value, "min": 0, "max": 100, "aria_label": "Upload progress"}),
        html.BUTTON({"data-testid": "bump-progress", "@click": _bump}, "Bump"),
        Progress({"indeterminate": True, "aria_label": "Loading"}),
        html.H2({}, "Feedback bits"),
        html.DIV({"data-testid": "badge-row"}, Badge({"variant": "success"}, slots={"default": lambda: "Saved"})),
        Card(
            {},
            slots={"header": lambda: "Card title", "default": lambda: "Card body", "footer": lambda: "Card footer"},
        ),
    )


DisclosurePage.scoped_style = {}
