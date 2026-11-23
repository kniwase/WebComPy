---
title: Forms
description: Manage reactive form state and validation with use_field(), use_form(), two-way :bind attributes, and first-party UI form controls.
---

# Forms

WebComPy separates form state and validation (`webcompy.forms`) from form UI widgets (`webcompy.ui`). A `Field` wraps a reactive `Signal` with `touched`, `dirty`, and validator `errors`; `Form` groups multiple fields to manage form-wide validity, submission state, and resets; and native HTML elements or first-party UI form controls bind cleanly to those fields.

## At a glance

```python
from typing import Any

from webcompy import use_computed, use_state
from webcompy.components import ComponentContext, define_component
from webcompy.elements import html
from webcompy.forms import email, min_length, required, use_field, use_form
from webcompy.ui import Checkbox, FormField, Input, Select


@define_component()
def SignupForm(context: ComponentContext[None]):
    name_field = use_field(
        use_state(lambda: ""),
        validators=[required(), min_length(3)],
        name="name",
    )
    email_field = use_field(
        use_state(lambda: ""),
        validators=[required(), email()],
        name="email",
    )
    role_field = use_field(use_state(lambda: "user"), name="role")
    agree_field = use_field(
        use_state(lambda: False),
        validators=[lambda v: None if v else "Accept the terms to continue"],
        name="agree",
    )
    form = use_form(name=name_field, email=email_field, role=role_field, agree=agree_field)
    status = use_state(lambda: "")

    def on_submit(values: dict[str, Any]):
        status.value = f"Registered {values['name']} ({values['role']})"

    return html.FORM(
        {"@submit": form.submit(on_submit)},
        FormField(
            {"field": name_field, "label": "Name"},
            slots={"default": lambda: Input({"field": name_field, "placeholder": "Your name"})},
        ),
        FormField(
            {"field": email_field, "label": "Email"},
            slots={"default": lambda: Input({"field": email_field, "input_type": "email"})},
        ),
        FormField(
            {"field": role_field, "label": "Role"},
            slots={
                "default": lambda: Select(
                    {
                        "field": role_field,
                        "options": [
                            {"value": "user", "label": "User"},
                            {"value": "admin", "label": "Admin"},
                        ],
                    }
                )
            },
        ),
        FormField(
            {"field": agree_field, "label": "I accept the terms"},
            slots={"default": lambda: Checkbox({"field": agree_field})},
        ),
        html.BUTTON({"type": "submit", "disabled": form.submitting}, "Submit"),
        html.P({}, use_computed(lambda: status.value)),
    )
```

## Reactive fields and validators

Create a `Field` with `use_field(signal, *, validators=(), name=None)`:

- `field.value`: the underlying `Signal[T]` holding the field's current value.
- `field.dirty`: `Signal[bool]` flipped to `True` on user input via `:bind`.
- `field.touched`: `Signal[bool]` flipped to `True` on blur via `:bind` (or when `form.touch_all()` runs).
- `field.errors`: `Computed[list[str]]` collecting error messages returned by validators.
- `field.valid` / `field.invalid`: `Computed[bool]` derived from `errors`.
- `field.reset()`: restores the initial value and clears `touched` and `dirty`.

Validators are callables taking the value and returning `None` (valid) or an error message `str`. Import built-in validators from `webcompy.forms`:

| Validator | Signature | Checks |
|---|---|---|
| `required` | `required(message="This field is required")` | Non-empty (`None`, `""`, whitespace-only, `False`, empty collections fail) |
| `min_length` | `min_length(n, message=None)` | `len(val) >= n` |
| `max_length` | `max_length(n, message=None)` | `len(val) <= n` |
| `min_value` | `min_value(n, message=None)` | `val >= n` |
| `max_value` | `max_value(n, message=None)` | `val <= n` |
| `pattern` | `pattern(regex, message="Invalid format")` | Regular expression match |
| `email` | `email(message="Invalid email address")` | Email format validation |

## Grouping fields with `use_form()`

Combine fields into a `Form` via `use_form(**fields)`:

- `form.valid`, `form.invalid`, `form.touched`, `form.dirty`: aggregate `Computed[bool]` properties across all member fields.
- `form.values()`: returns a `dict[str, Any]` snapshot of current field values keyed by field name.
- `form.touch_all()` and `form.reset()`: mark all fields touched or reset every field to initial state.
- `form.submit(handler)`: returns an `@submit` event handler that calls `ev.preventDefault()`, touches all fields, and aborts if `form.valid.value` is `False`. When valid, it invokes `handler(values)` (sync or `async def`), tracking progress in `form.submitting` (`Signal[bool]`) and capturing exceptions in `form.submit_error`.

## Native two-way `:bind` wiring

You can also bind native HTML form elements directly to any `Field` or writable `Signal` via `{":bind": field}`:

```python
from webcompy import use_state
from webcompy.elements import html
from webcompy.forms import required, use_field

username = use_field(use_state(lambda: ""), validators=[required()])

html.INPUT({":bind": username, "type": "text", "placeholder": "Username"})
```

`:bind` works on `<input>` (`text`, `email`, `password`, `search`, `tel`, `url`, `number`, `checkbox`, `radio` with static `value`), `<textarea>`, and single-value `<select>`. It synchronizes the DOM value/checked state two-way, sets `field.dirty.value = True` on input/change, and sets `field.touched.value = True` on `blur` when bound to a `Field`.

## First-party UI form controls

`webcompy.ui` provides styled, accessible form components designed to pair with `Field` (or raw `value` + `on_change` for standalone controls):

| Component | Purpose | Key props |
|---|---|---|
| `Input` | Single-line text/number/email input | `field`, `value`, `on_change`, `input_type`, `placeholder`, `disabled`, `required` |
| `Textarea` | Multi-line text input | `field`, `value`, `on_change`, `rows`, `placeholder`, `disabled`, `required` |
| `Select` | Option dropdown (`options=[{"value", "label"}]`) | `field`, `value`, `on_change`, `options`, `disabled`, `required` |
| `Checkbox` | Boolean checkbox with optional inline label | `field`, `value`, `on_change`, `label`, `disabled`, `required` |
| `Switch` | Accessible toggle switch (`role="switch"`) | `field`, `value`, `on_change`, `label`, `disabled`, `required` |
| `Radio` | Single radio button bound to one `option_value` | `field`, `value`, `on_change`, `option_value`, `name`, `disabled` |
| `RadioGroup` | Fieldset radio group with `<legend>` | `field`, `value`, `on_change`, `options`, `legend`, `disabled`, `required` |
| `FormField` | Wrapper pairing `<label>`, slotted control, and error region | `field`, `label`, `control_id`, `error_id` (`default` slot) |

Inside `FormField`, validation error messages stay hidden until `field.touched.value` is `True` (so new forms never flash red errors on initial load) and link automatically via `aria-invalid` and `aria-describedby`. For `RadioGroup`, the group renders its own `<legend>` via `legend=`, so omit `label` on the outer `FormField`.

## Notes & caveats

- Pass **either** `field` **or** `value` + `on_change` to a UI form control — the two modes are mutually exclusive.
- Native `:bind` cannot be combined with an explicit `value` (or `checked` on checkboxes/radios) or dynamic `type` attribute on the same element.
- Prefer creating underlying signals with `use_state(...)` inside component setup so initial field values survive SSR hydration cleanly.

## Next steps

- Learn how first-party headless and themed layers work in [UI Primitives](/documents/basic/ui-primitives).
- Submit validated form data to an API in [HTTP & Async](/documents/basic/http-and-async).
- Advanced topics coming in Advanced Usage: headless form contracts, `data-state` attributes, and DI-scoped `FormField` wiring.
