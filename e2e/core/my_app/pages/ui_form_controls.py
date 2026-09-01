"""UI form controls E2E page."""

from typing import Any

from webcompy.components import ComponentContext, define_component
from webcompy.elements import html
from webcompy.forms import min_length, required, use_field, use_form
from webcompy.signal import use_computed, use_state
from webcompy.ui import Checkbox, FormField, Input, RadioGroup, Select, Switch, Textarea


@define_component()
def UiFormControlsPage(context: ComponentContext[None]) -> Any:
    """E2E page for ui form controls."""

    context.set_title("UI Form Controls - E2E")

    name_field = use_field(use_state(lambda: ""), validators=[required(), min_length(2)], name="name")
    bio_field = use_field(use_state(lambda: ""), name="bio")
    country_field = use_field(use_state(lambda: ""), validators=[required()], name="country")
    agree_field = use_field(use_state(lambda: False), validators=[lambda v: None if v else "agree"], name="agree")
    plan_field = use_field(use_state(lambda: ""), validators=[required()], name="plan")
    notify_field = use_field(use_state(lambda: False), name="notify")
    form = use_form(name=name_field, bio=bio_field, country=country_field, agree=agree_field, plan=plan_field)

    status = use_state(lambda: "idle")

    def _on_submit(_values: dict[str, Any]) -> None:
        status.value = "submitted"

    def _on_reset(_ev: Any) -> None:
        form.reset()
        status.value = "idle"

    return html.DIV(
        {"data-testid": "ui-form-controls-page"},
        html.H2({}, "UI Form Controls Tests"),
        html.FORM(
            {"@submit": form.submit(_on_submit), "data-testid": "ufc-form"},
            FormField(
                {"field": name_field, "label": "Name", "class_name": "ufc-name-field"},
                slots={"default": lambda: Input({"field": name_field})},  # type: ignore[arg-type]
            ),
            FormField(
                {"field": bio_field, "label": "Bio", "class_name": "ufc-bio-field"},
                slots={"default": lambda: Textarea({"field": bio_field, "rows": 3})},  # type: ignore[arg-type]
            ),
            FormField(
                {"field": country_field, "label": "Country", "class_name": "ufc-country-field"},
                slots={  # type: ignore[arg-type]
                    "default": lambda: Select(
                        {
                            "field": country_field,
                            "options": [
                                {"value": "", "label": "Choose…"},
                                {"value": "jp", "label": "Japan"},
                                {"value": "us", "label": "USA"},
                            ],
                        }
                    )
                },
            ),
            FormField(
                {"field": agree_field, "class_name": "ufc-agree-field"},
                slots={  # type: ignore[arg-type]
                    "default": lambda: Checkbox({"field": agree_field, "label": "I agree"})
                },
            ),
            FormField(
                {"field": notify_field, "class_name": "ufc-notify-field"},
                slots={  # type: ignore[arg-type]
                    "default": lambda: Switch({"field": notify_field, "aria_label": "Email notifications"})
                },
            ),
            FormField(
                {"field": plan_field, "class_name": "ufc-plan-field"},
                slots={  # type: ignore[arg-type]
                    "default": lambda: RadioGroup(
                        {
                            "field": plan_field,
                            "legend": "Plan",
                            "options": [
                                {"value": "free", "label": "Free"},
                                {"value": "pro", "label": "Pro"},
                            ],
                        }
                    )
                },
            ),
            html.DIV(
                {"class": "ufc-actions"},
                html.BUTTON({"type": "submit", "data-testid": "ufc-submit"}, "Submit"),
                html.BUTTON({"type": "button", "data-testid": "ufc-reset", "@click": _on_reset}, "Reset"),
            ),
        ),
        html.P({"data-testid": "ufc-status"}, use_computed(lambda: status.value)),
    )
