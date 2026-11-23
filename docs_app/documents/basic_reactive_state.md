---
title: Reactive State
description: Manage fine-grained UI state with Signal, Computed, ReactiveList, ReactiveDict, transfer-capable use_* composables, and effect().
---

# Reactive State

WebComPy tracks state dependencies automatically with fine-grained reactive primitives. When a signal changes, only the text nodes, attributes, conditionals, or list items that read it update — without re-running component setup or diffing a whole virtual tree.

Use the `use_*` composables inside component setup for stateful UI (especially when pre-rendering with SSR/SSG), and standalone `Signal` / `Computed` objects for module-level or non-component state.

## At a glance

```python
from webcompy import use_computed, use_state
from webcompy.components import ComponentContext, define_component
from webcompy.elements import html


@define_component()
def ClickCounter(context: ComponentContext[None]):
    count = use_state(lambda: 0)

    @use_computed
    def summary():
        return f"Clicked {count.value} times"

    return html.DIV(
        {},
        html.P({}, summary),
        html.BUTTON({"@click": lambda _ev: setattr(count, "value", count.value + 1)}, "Increment"),
    )
```

## Reactive primitives

Import primitives directly from `webcompy.signal`:

- **`Signal(initial)`**: mutable reactive cell. Read or assign via `.value`.
- **`Computed(fn)`**: read-only derived signal that tracks every reactive object read inside `fn` and recomputes automatically when dependencies change.
- **`ReactiveList(initial)`**: reactive `list`-like container (`append`, `extend`, `insert`, `pop`, `remove`, `clear`, `reverse`, `sort`, slice/index mutation, and replacement via `.value = [...]`).
- **`ReactiveDict(initial)`**: reactive `dict`-like mapping (`d[k] = v`, `del d[k]`, `update`, `pop`, `clear`, `setdefault`, and replacement via `.value = {...}`).

```python
from webcompy.signal import Computed, ReactiveDict, ReactiveList, Signal

price = Signal(100)
qty = Signal(2)
total = Computed(lambda: price.value * qty.value)

items = ReactiveList(["Notebook", "Pen"])
items.append("Eraser")  # notifies consumers reading items

settings = ReactiveDict({"compact": False})
settings["compact"] = True
```

## Transfer-capable `use_*` composables

Inside a component setup function, prefer the `use_*` family (exported from top-level `webcompy` and `webcompy.signal`):

| Composable | Underlying primitive | Signature |
|---|---|---|
| `use_state` | `Signal[T]` | `use_state(lambda: initial)` or `use_state("key", lambda: initial)` |
| `use_computed` | `Computed[T]` | `use_computed(lambda: ...)` or as `@use_computed` decorator |
| `use_reactive_list` | `ReactiveList[V]` | `use_reactive_list(lambda: [...])` or `use_reactive_list("key", lambda: [...])` |
| `use_reactive_dict` | `ReactiveDict[K, V]` | `use_reactive_dict(lambda: {...})` or `use_reactive_dict("key", lambda: {...})` |

```python
from webcompy import use_computed, use_reactive_list, use_state

count = use_state(lambda: 1)
tags = use_reactive_list(lambda: ["python", "webcompy"])
tag_count = use_computed(lambda: f"{len(tags.value)} tags")
```

Passing a factory callable (`lambda: ...`) lets WebComPy **skip invoking the factory during browser hydration** when matching state was transferred from server-side rendering (SSR/SSG). Passing an explicit key string (optional first argument) gives the state slot a custom identifier inside that component.

## The equality contract

WebComPy state primitives are **cells**: assigning `sig.value = new_val` compares `new_val == current` first. If the new value equals the current value, no downstream `Computed`, DOM binding, or `effect` is notified.

- Replace immutable structures or create updated copies (`items.append(...)` or `user.value = {**user.value, "name": "Bob"}`) rather than mutating a plain Python `list` or `dict` stored inside a plain `Signal` in place — mutating an un-tracked container keeps the same object identity and fails equality checks.
- For reactive collections, use `ReactiveList` / `ReactiveDict` (and `use_reactive_list` / `use_reactive_dict`) so mutations trigger fine-grained notifications.

## Side effects with `effect()`

Run reactive side effects whenever tracked signals change using `effect(fn, on_cleanup=None)`:

```python
from webcompy.signal import effect, use_state

query = use_state(lambda: "")


def sync_label():
    print("Current query:", query.value)


handle = effect(sync_label)
```

- `fn` runs immediately once to discover its signal dependencies, then re-runs whenever any dependency changes.
- Return a cleanup function or pass `on_cleanup=` to clean up before the next run and on disposal.
- Effects created inside a component setup belong to that component's `EffectScope` and are disposed automatically when the component unmounts/destroys. When calling `effect()` outside a component, stop it manually via `handle.dispose()`.

## Notes & caveats

- `Computed` is read-only; assigning `.value` raises an error.
- Avoid creating side effects inside `Computed` functions — keep computed getters pure and put side effects in `effect()` or event handlers.
- Always use `use_*` composables inside component setup for state that should survive SSR-to-browser hydration seamlessly.

## Next steps

- Render reactive lists and conditional branches in [Elements & Events](/documents/basic/elements-and-events).
- For event streams (WebSocket/SSE message logs where duplicates must not be collapsed), see [Signals and Streams](/documents/advanced/signal-stream).
- For state written only by external browser events or callbacks, see [Read-only Signals and Events](/documents/advanced/readonly-signal).
