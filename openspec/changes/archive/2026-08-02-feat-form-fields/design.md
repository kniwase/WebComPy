# Design: Form Fields (`use_field` / `use_form`)

## Context

**Goal of this document**: enable a fresh session to implement form fields correctly per intent. Prerequisites: `feat-two-way-binding` is merged, providing `expand_bind_attr(tag_name, attrs, events)` in `packages/webcompy/src/webcompy/elements/_bind.py` (accepts writable `Signal` in `:bind`, expands to bound attr + write-back handler).

### Why field-first (decided, not open)

Angular Signal Forms uses a model-first design (`form(model_signal)` explodes one object signal into a FieldTree) because Angular lacks per-field primitive signals in user code. WebComPy has first-class per-field `Signal`s via `use_state`, so the idiomatic design is: **one `Signal` per field, wrapped by a `Field` object**; a `Form` is a flat aggregation of fields. Model-first/schema APIs were explicitly rejected by the project owner.

### Existing pieces reused

- `Signal` / `Computed` (`webcompy/signal/`): Field state is plain Signals; errors/validity are Computeds (lazy, equality-suppressed).
- `:bind` expansion (`webcompy/elements/_bind.py`, from `feat-two-way-binding`): the single point where Field integration hooks in.
- Event lifecycle: blur/input handlers must go into the `events` dict inside `expand_bind_attr`, inheriting `create_proxy`/`destroy` management.
- `AsyncWrapper` (`webcompy/aio/_aio.py`) for running async submit handlers.
- `DOMEvent.preventDefault()` exists on the port layer (`webcompy/ports/_dom.py:36`).

## Goals / Non-Goals

**Goals:**

- `Field` wrapper with reactive validation state (`errors`/`valid`/`invalid`) and interaction state (`touched`/`dirty`).
- Seven built-in validators with optional custom messages.
- `:bind` accepts `Field`: binds `field.value`, wires blur→touched, edit→dirty.
- `Form` aggregation with `submit()` orchestration (preventDefault, touch-all, validity gate, async handler, `submitting`/`submit_error`).
- SSR-safe: no events server-side; initial render shows initial validation state.

**Non-Goals:** async validators, `<select>`, schema/model-first API, i18n of built-in messages, dedicated cross-field API, auto form rendering.

## Decisions

### D1. New package `webcompy/forms/`

```
packages/webcompy/src/webcompy/forms/
    __init__.py        # public exports: Field, Form, use_field, use_form, validators
    _field.py          # Field class
    _validators.py     # Validator type + built-ins
    _form.py           # Form class + use_form
```

Import direction: `forms` depends on `signal` only. `elements/_bind.py` imports `Field` from `webcompy.forms._field` — **no cycle** (forms does NOT import elements). Public import path: `from webcompy.forms import use_field, use_form, required, ...`.

### D2. `Field` is a plain wrapper object, not a SignalBase

```python
# webcompy/forms/_field.py (sketch)
Validator = Callable[[T], str | None]

class Field(Generic[T]):
    def __init__(self, signal: Signal[T], validators: Iterable[Validator[T]], name: str | None = None):
        self.name = name
        self.value: Signal[T] = signal              # the same object, exposed
        self.touched: Signal[bool] = Signal(False)
        self.dirty: Signal[bool] = Signal(False)
        self._validators = list(validators)
        self._initial = signal.value                # captured for reset()
        self.errors: Computed[list[str]] = Computed(self._validate)
        self.valid: Computed[bool] = Computed(lambda: len(self.errors.value) == 0)
        self.invalid: Computed[bool] = Computed(lambda: not self.valid.value)

    def _validate(self) -> list[str]:
        return [msg for v in self._validators if (msg := v(self.value.value)) is not None]

    def reset(self) -> None:
        self.value.value = self._initial
        self.touched.value = False
        self.dirty.value = False

def use_field(signal, *, validators=(), name=None) -> Field: return Field(signal, validators, name)
```

- `Field` deliberately does NOT subclass `SignalBase`: passing a Field anywhere a Signal is expected (other than `:bind`) is a type error, keeping semantics explicit.
- `touched`/`dirty` are plain `Signal`s (not `use_state`): they are transient UI state and MUST NOT participate in SSR transfer.
- `errors` recomputes on every value change (Computed dependency on `self.value`). There is no separate "validate on submit only" mode in v1; display gating uses `touched`.
- `use_field` does not require component-setup context (no DI, no transfer); it MAY be called anywhere. Documented as typically called in setup.

### D3. Built-in validators return message-or-None callables

```python
# webcompy/forms/_validators.py (sketch)
def required(message: str = "This field is required") -> Validator[Any]:
    def validate(v):
        if v is None or (isinstance(v, str) and not v.strip()) or v is False:
            return message
        return None
    return validate
```

- `required` treats `None`, whitespace-only `str`, and `False` as missing (the `False` rule makes "must agree" checkboxes work).
- `min_length(n)` / `max_length(n)`: on `len(value)`; non-sized values raise `WebComPyException` at validation time (developer error).
- `pattern(regex, message)`: `re.search` on str values.
- `email(message)`: pragmatic regex `^[^@\s]+@[^@\s]+\.[^@\s]+$` — documented as intentionally non-RFC-complete.
- `min_value(n)` / `max_value(n)`: numeric comparison; named `min_value`/`max_value` (NOT `min`/`max`) to avoid shadowing builtins.
- All factories accept an optional custom message (i18n escape hatch).

### D4. `:bind` + Field wiring (extends `_bind.py`)

`expand_bind_attr` gains a Field branch before the Signal-kind check:

- Detect via `isinstance(value, Field)` (import from `webcompy.forms._field`).
- Use `field.value` as the bound signal; all existing per-element rules/conversions apply unchanged.
- Write-back handler: set `field.dirty.value = True` before updating the value.
- Register an additional `blur` handler: `field.touched.value = True`, chained with any user `@blur` (touched first). Uses the same chaining convention as `feat-two-way-binding` D7.
- Field with an incompatible value type hits the same type-discipline errors (the Field branch delegates to the same checks on `field.value`).

### D5. `Form` aggregates fields flatly; `submit` returns an event handler

```python
# webcompy/forms/_form.py (sketch)
class Form:
    def __init__(self, fields: dict[str, Field]):
        self.fields = fields
        self.valid = Computed(lambda: all(f.valid.value for f in fields.values()))
        self.invalid = Computed(lambda: not self.valid.value)
        self.touched = Computed(lambda: any(f.touched.value for f in fields.values()))
        self.dirty = Computed(lambda: any(f.dirty.value for f in fields.values()))
        self.submitting: Signal[bool] = Signal(False)
        self.submit_error: Signal[BaseException | None] = Signal(None)

    def touch_all(self) -> None: ...
    def reset(self) -> None: ...            # resets every field
    def values(self) -> dict[str, Any]: ... # {name: f.value.value}

    def submit(self, handler):
        def on_submit(ev):
            ev.preventDefault()
            self.touch_all()
            if not self.valid.value:
                return
            async def run():
                self.submitting.value = True
                self.submit_error.value = None
                try:
                    result = handler(self.values())
                    if isawaitable(result):
                        await result
                except BaseException as err:      # noqa: BLE001 - surfaced via submit_error
                    self.submit_error.value = err
                finally:
                    self.submitting.value = False
            AsyncWrapper()(run)()
        return on_submit

def use_form(**fields) -> Form: return Form(fields)
```

Usage: `html.FORM({"@submit": form.submit(on_login)}, ...)`. The validity gate happens AFTER `touch_all` so all errors become visible on a failed submit. `submit_error` captures handler exceptions instead of crashing the event loop; re-raise behavior is template/app logic.

### D6. SSR and hydration

All Field/Form state derives from Signals/Computeds — SSR renders initial values and initial validation results with no special-casing. `touched`/`dirty` are always `False` on SSR and on first hydration (not transferred), so error displays gated on `touched` never flash on page load.

### D7. Template usage is ordinary attribute/expression access

`{% if email_field.touched.value and email_field.invalid.value %}` — `Attribute` access on the Field object, then `.value` on Signals, both already whitelisted in the expression language. `{{ email_field.errors.value | join(', ') }}` works via filters. No template-engine changes in this change.

## Risks / Trade-offs

- [Validation runs on every keystroke (Computed)] → messages are cheap string checks; equality suppression prevents redundant DOM updates; display gating via `touched` avoids UX noise.
- [`submit` swallows handler exceptions into `submit_error`] → documented; apps that want propagation can read and re-raise in an `effect`.
- [`elements/_bind.py` importing `forms`] → one-way dependency (elements → forms → signal), verified cycle-free; `webcompy.forms` is part of the core browser wheel.
- [Field not being SignalBase surprises users expecting to pass it as attr] → clear error message from existing attr pipeline ("Cannot convert Field..."), docs recommend `field.value` in those positions.

## Migration Plan

Additive only. Manual validation patterns keep working. After this merges, docs/demos may adopt `use_field` in a follow-up.

## Open Questions

None.
