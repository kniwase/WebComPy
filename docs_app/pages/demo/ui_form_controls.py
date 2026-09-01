from typing import Any

from webcompy.components import ComponentContext, define_component
from webcompy.elements import html

from ...components.demo_display import DemoDisplay
from ...components.ui import DocsSection


@define_component()
def UiFormControlsDemoPage(context: ComponentContext[None]) -> Any:
    context.set_title("UI Form Controls - WebCompy Demo")
    return html.DIV(
        {"class": "page-container"},
        html.H1({"class": "page-title"}, "UI Form Controls"),
        html.P(
            {"class": "page-lead"},
            "First-party form controls as headless/themed pairs: Input, Textarea, Select, Checkbox, "
            "Switch, RadioGroup, and the FormField wrapper that composes label, control, and "
            "accessible error region over the forms module's Field binding.",
        ),
        DemoDisplay(
            {
                "title": "UI Form Controls",
                "app_name": "ui_form_controls",
                "demo_path": "/_demos/ui_form_controls/app.py",
            },
        ),
        DocsSection(
            {"heading": "Binding contract"},
            slots={
                "default": lambda: html.P(
                    {},
                    "Every control accepts either a forms-module Field (bound through the framework "
                    ":bind mechanism, so value sync, dirty on write-back, and touched on blur come for "
                    "free) or a raw value plus an on_change callback. The two modes are mutually "
                    "exclusive. Select binds a string-valued field to native option values; Switch "
                    'exposes the role="switch" pattern with aria-checked over a native checkbox.',
                )
            },
        ),
        DocsSection(
            {"heading": "FormField wiring"},
            slots={
                "default": lambda: html.P(
                    {},
                    "FormField provides hydration-stable association ids through the component DI "
                    "scope: the slotted control receives the id referenced by the caption's label for, "
                    "and while the field is touched and invalid it carries aria-invalid plus an "
                    "aria-describedby link to the error region. Errors never flash on load because the "
                    "display is gated on touched. Group controls like RadioGroup self-label with a "
                    "legend, so the wrapper omits its label prop for them.",
                )
            },
        ),
        DocsSection(
            {"heading": "State vocabulary"},
            slots={
                "default": lambda: html.P(
                    {},
                    'Bound controls expose data-state="valid" and flip to data-state="invalid" in '
                    "the touched-invalid state, matching the headless contract's state attributes. The "
                    "themed layer styles borders, focus-visible rings, disabled, and invalid states "
                    "from semantic design tokens in the primitives stylesheet.",
                )
            },
        ),
    )
