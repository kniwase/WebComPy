"""Standalone docs demo: a complete form built from ui form controls."""

from typing import Any

from webcompy.app import WebComPyApp
from webcompy.components import ComponentContext, define_component
from webcompy.elements import html
from webcompy.forms import email, min_length, required, use_field, use_form
from webcompy.signal import use_computed, use_state
from webcompy.ui import Checkbox, FormField, Input, RadioGroup, Select, Switch, Textarea


@define_component("ui-form-controls-demo-app")
def UiFormControlsDemo(_: ComponentContext[None]) -> Any:
    name_field = use_field(
        use_state(lambda: ""), validators=[required(), min_length(3, "At least 3 characters")], name="name"
    )
    email_field = use_field(use_state(lambda: ""), validators=[required(), email()], name="email")
    country_field = use_field(use_state(lambda: ""), validators=[required()], name="country")
    notes_field = use_field(use_state(lambda: ""), name="notes")
    updates_field = use_field(use_state(lambda: True), name="updates")
    marketing_field = use_field(use_state(lambda: False), name="marketing")
    plan_field = use_field(use_state(lambda: "free"), validators=[required()], name="plan")
    agree_field = use_field(
        use_state(lambda: False), validators=[lambda v: None if v else "Please accept the terms"], name="agree"
    )

    form = use_form(
        name=name_field,
        email=email_field,
        country=country_field,
        plan=plan_field,
        agree=agree_field,
    )

    submitted = use_state(lambda: "")

    def _on_submit(values: dict[str, Any]) -> None:
        submitted.value = f"Welcome, {values['name']} ({values['plan']} plan)!"

    def _on_reset(_ev: Any) -> None:
        form.reset()
        submitted.value = ""

    return html.DIV(
        {"class": "ufc-demo"},
        html.H1({}, "UI Form Controls Demo"),
        html.P({}, "Themed form controls with Field binding, validation on blur, and accessible error wiring."),
        html.FORM(
            {"@submit": form.submit(_on_submit)},
            FormField(
                {"field": name_field, "label": "Name"},
                slots={"default": lambda: Input({"field": name_field, "placeholder": "Your name"})},
            ),
            FormField(
                {"field": email_field, "label": "Email"},
                slots={
                    "default": lambda: Input(
                        {"field": email_field, "input_type": "email", "placeholder": "you@example.com"}
                    )
                },
            ),
            FormField(
                {"field": country_field, "label": "Country"},
                slots={
                    "default": lambda: Select(
                        {
                            "field": country_field,
                            "options": [
                                {"value": "", "label": "Choose your country…"},
                                {"value": "jp", "label": "Japan"},
                                {"value": "us", "label": "United States"},
                                {"value": "de", "label": "Germany"},
                            ],
                        }
                    )
                },
            ),
            FormField(
                {"field": notes_field, "label": "Notes"},
                slots={"default": lambda: Textarea({"field": notes_field, "rows": 3, "placeholder": "Anything else?"})},
            ),
            FormField(
                {"field": plan_field},
                slots={
                    "default": lambda: RadioGroup(
                        {
                            "field": plan_field,
                            "legend": "Plan",
                            "options": [
                                {"value": "free", "label": "Free"},
                                {"value": "pro", "label": "Pro"},
                                {"value": "team", "label": "Team"},
                            ],
                        }
                    )
                },
            ),
            html.DIV(
                {"class": "ufc-demo-toggles"},
                FormField(
                    {"field": agree_field, "label": "I accept the terms"},
                    slots={"default": lambda: Checkbox({"field": agree_field})},
                ),
                Switch({"field": updates_field, "label": "Product updates"}),
                Switch({"field": marketing_field, "label": "Marketing emails"}),
            ),
            html.DIV(
                {"class": "ufc-demo-actions"},
                html.BUTTON({"type": "submit", "id": "ufc-demo-submit"}, "Submit"),
                html.BUTTON({"type": "button", "id": "ufc-demo-reset", "@click": _on_reset}, "Reset"),
            ),
        ),
        html.P({"id": "ufc-demo-status"}, use_computed(lambda: submitted.value)),
    )


UiFormControlsDemo.scoped_style = {
    ".ufc-demo": {
        "font-family": "sans-serif",
        "padding": "1rem",
        "max-width": "28rem",
    },
    ".ufc-demo form": {
        "display": "flex",
        "flex-direction": "column",
        "gap": "0.75rem",
    },
    ".ufc-demo-toggles": {
        "display": "flex",
        "flex-wrap": "wrap",
        "gap": "1rem",
        "align-items": "center",
    },
    ".ufc-demo-actions": {
        "display": "flex",
        "gap": "0.5rem",
        "margin-top": "0.5rem",
    },
    ".ufc-demo-actions button": {
        "padding": "0.5rem 1rem",
        "cursor": "pointer",
    },
    "#ufc-demo-status": {
        "margin-top": "0.75rem",
        "font-weight": "600",
    },
}

app = WebComPyApp(root_component=UiFormControlsDemo)
app.run()
