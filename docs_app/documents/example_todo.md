---
title: ToDo List
description: Reactive list and dictionary mutations, fine-grained derived counts, DomNodeRef inputs, child components, and scoped CSS in a browser ToDo app.
---

# ToDo List

This example builds a client-side ToDo application where adding tasks, appending or removing items with `ReactiveDict`, toggling completion checkboxes, and deriving conditional inline styles happen reactively without manual DOM syncing.

Use this pattern whenever a view manages a growing and shrinking collection of interactive items with per-row reactive state.

## What this demonstrates

- **Collection mutations with counts**: Mutating `data[new_id] = ...` and `del data[k]` inside `use_reactive_dict` updates `repeat(data, lambda v, k: ToDoItem(v))` surgically, inserting or removing only the affected `<li>` nodes while leaving sibling DOM nodes untouched (covering dynamic list growth, shrinkage, and derived item styling).
- **Per-item nested signals**: Storing `"title"` and `"done"` as nested `Signal`s lets clicking a checkbox toggle `"text-decoration: line-through;"` via `use_computed(...)` without re-creating the whole list item.
- **Uncontrolled input reading via `DomNodeRef`**: Attaching `{":ref": input_ref}` lets `"Add ToDo"` read `input_ref.value` and clear the field directly on submit.
- **Isolated scoped CSS**: Styles declared on `ToDoItem.scoped_style` and `TodoApp.scoped_style` only target elements within each component boundary.

## Key mechanisms and how to adapt

1. **Keyed filtering vs. direct removal**: Switch `repeat(data, ...)` to iterate over a `use_computed(...)` filtered slice paired with `key=lambda item: item["id"]` when you want view filters like All / Active / Done to preserve existing list nodes.
2. **Use `use_reactive_list` for ordered sequences**: Replace `use_reactive_dict` with `use_reactive_list(lambda: [...])` when item order or positional inserts matter more than UUID keys.
3. **Upgrade inputs to validated fields**: Replace raw `DomNodeRef` inputs with `use_field()` and `use_form()` when adding validation messages or async submit states.

## Next steps

- See validated form inputs and accessible error wiring next in [Forms](/documents/examples/forms).
- Review fine-grained signals, `ReactiveDict`, `ReactiveList`, and `repeat()` in [Reactive State](/documents/basic/reactive-state) and [Elements & Events](/documents/basic/elements-and-events).
- Follow the six-part guided tutorial starting at [Step 1: App Shell](/documents/guides/todo-app-shell).
