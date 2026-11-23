---
title: Elements & Events
description: Build reactive DOM trees directly in Python with the html namespace, repeat(), switch(), DOMEvent handlers, and DomNodeRef.
---

# Elements & Events

Alongside HTML templates, WebComPy lets you construct DOM trees directly in Python via `webcompy.elements`. Python element trees give you full IDE autocomplete, type checking, dynamic composition, and direct control over keyed list updates and conditional branches.

## At a glance

```python
from webcompy import use_computed, use_state
from webcompy.components import ComponentContext, define_component
from webcompy.elements import DOMEvent, html


@define_component()
def StepperControl(context: ComponentContext[None]):
    step = use_state(lambda: 1)

    def increment(_ev: DOMEvent):
        step.value += 1

    return html.DIV(
        {"class": "stepper"},
        html.SPAN({}, use_computed(lambda: f"Step: {step.value}")),
        html.BUTTON({"type": "button", "@click": increment}, "+1"),
    )
```

## The `html` namespace and element structure

Every HTML tag is available as an uppercase factory on `html` (e.g., `html.DIV`, `html.P`, `html.BUTTON`, `html.INPUT`, `html.UL`, `html.LI`):

- **First argument**: attributes dictionary (`{"class": "card", "disabled": is_disabled, "@click": on_click}`).
- **Remaining arguments (`*children`)**: strings, `Element`s, `Component`s, `SignalBase` values, or `None` (skipped).
- **Boolean & reactive attributes**: passing `True` sets a valueless boolean attribute (`disabled`); passing `False` or `None` omits it. Any attribute value can be a `Signal` or `Computed` that stays synced with the DOM.

### Text, line breaks, raw HTML, and fragments

- `text(val, enable_multiline=True)` renders a text node (splitting newlines into `<br>` when `enable_multiline=True`).
- `break_line()` creates a `<br>` node.
- `raw_html(html_str_or_signal, wrapper="span")` injects raw HTML inside a wrapper element — only use this with trusted markup.
- Returning a `list` or `tuple` directly from a component acts as a fragment with multiple sibling root nodes.

## Conditional rendering with `switch()`

Render the first matching reactive branch without tearing down surrounding elements:

```python
from webcompy import use_computed, use_state
from webcompy.elements import html, switch

status = use_state(lambda: "loading")

view = switch(
    {"case": use_computed(lambda: status.value == "loading"), "generator": lambda: html.P({}, "Loading...")},
    {"case": use_computed(lambda: status.value == "ready"), "generator": lambda: html.P({}, "Ready!")},
    default=lambda: html.P({}, "Idle"),
)
```

Each branch takes a `{"case": signal, "generator": lambda: ...}` mapping and an optional `default=lambda: ...` fallback. Generators run lazily only when that branch becomes active.

## Lists and keyed reconciliation with `repeat()`

Render reactive lists (`ReactiveList`) or reactive dicts (`ReactiveDict`) using `repeat(sequence, template, key=None)`:

```python
from webcompy import use_reactive_list
from webcompy.elements import html, repeat

todos = use_reactive_list(
    lambda: [
        {"id": 1, "text": "Write docs"},
        {"id": 2, "text": "Run tests"},
    ]
)

todo_list = html.UL(
    {},
    repeat(
        todos,
        lambda item, _key: html.LI({}, item["text"]),
        key=lambda item: item["id"],
    ),
)
```

- **Keyed lists (`key=`)**: pass a function returning a unique stable key (`int` or `str`) from each item. When `key=` is provided, `template` receives `(item, derived_key)` and WebComPy reuses existing DOM nodes across insertions, deletions, and reorders instead of rebuilding the whole list.
- **Plain `ReactiveList` without `key=`**: `template` receives `(item,)` (or `(item, index)`).
- **`ReactiveDict`**: keys are already intrinsic, so omit `key=` and accept `(value, dict_key)` or `(value,)` in `template`.

## DOM events and `DOMEvent`

Prefix event keys with `"@"` inside an element's attributes mapping (`"@click"`, `"@input"`, `"@submit"`, `"@keydown"`, or `event("click")`):

```python
from webcompy.elements import DOMEvent, html


def handle_submit(ev: DOMEvent):
    ev.preventDefault()
    ev.stopPropagation()
    print("Submitted!")


html.FORM({"@submit": handle_submit}, html.BUTTON({"type": "submit"}, "Send"))
```

Handlers receive a `DOMEvent` wrapping the browser event (`ev.target`, `ev.preventDefault()`, `ev.stopPropagation()`). Event handlers may also be `async def` coroutines — WebComPy schedules them automatically and routes uncaught exceptions to any ancestor `ErrorBoundary`.

## Capturing DOM nodes with `DomNodeRef`

When you need imperative browser DOM access (focusing an `<input>`, measuring dimensions, integrating a canvas/chart library), attach a `DomNodeRef` using `noderef` (or `":ref"`):

```python
from webcompy.components import ComponentContext, define_component, on_mounted
from webcompy.elements import DomNodeRef, html, noderef


@define_component()
def AutoFocusSearch(context: ComponentContext[None]):
    input_ref = DomNodeRef()

    @on_mounted
    def focus_on_mount():
        input_ref.focus()

    return html.INPUT({noderef: input_ref, "type": "search", "placeholder": "Search..."})
```

`DomNodeRef` proxies attribute access and method calls directly to the mounted DOM node (`input_ref.focus()`), or exposes the underlying `DOMNode` via `input_ref.element` (raising `WebComPyException` if accessed before mount).

## Notes & caveats

- Always call `input_ref` inside `@on_mounted` or event handlers, not directly during initial component setup before the DOM element exists.
- Prefer keyed `repeat(..., key=...)` for lists of interactive rows or inputs so focus and element state stay attached to the right item across reorders.

## Next steps

- See how WebComPy renders Markdown files into element trees in [Markdown Documents](/documents/basic/markdown-documents).
- Compare Python element helpers with [HTML Templates](/documents/basic/template-html).
- Use `:bind` and first-party form controls in [Forms](/documents/basic/forms).
