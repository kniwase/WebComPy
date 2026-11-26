# Design

## Context

See [proposal.md](proposal.md) for the root cause and scope. Across the virtual DOM element hierarchy (`ElementAbstract`), elements accept reactive inputs created either by user code (`Signal`, `use_computed`, `ReactiveList`, `ReactiveDict`, `ReadonlySignal`) or by the template/binding machinery (`_OwnedComputed`, internal `Computed`s for routing or radio `:bind`). Because `ElementAbstract` inherited `SignalReceivable.__setattr__`, storing a borrowed signal in `self._sequence`, `self._text`, `self._html`, `self._cases`, `self._to`, or `self._iterable` silently registered it in `__signal_members__`, causing `__purge_signal_members__()` to call `consumer_destroy()` on caller state during unmount or branch patching.

## Goals / Non-Goals

**Goals:**
- Prevent any VDOM element (`ElementAbstract` subclass) from implicitly claiming attributes via `SignalReceivable.__setattr__`.
- Ensure every framework-owned signal created by template binders, form `:bind`, `MultiLineTextElement`, `RouterLink`, `RouterView`, and component-tag prop interpolation is still destroyed once on its owner's teardown, with zero edge leaks.
- Prevent inner elements from claiming and destroying a `_OwnedComputed` that belongs to an enclosing component prop (`<Child title="Hi {{ name }}" />`) or template root (`AppDocumentRoot`).
- Preserve `SignalReceivable` implicit attribute tracking for direct non-element subclasses and `@computed_property` descriptor registration on all subclasses.

**Non-Goals:**
- Changing user-level `use_computed()` or `Computed()` lifetime semantics outside element/template ownership.
- Modifying `docs_app/` demo code.

## Decisions

### 1. Opt `ElementAbstract` out via C-level `object.__setattr__`

In `ElementAbstract`, define:
```python
if not TYPE_CHECKING:
    __setattr__ = object.__setattr__
```
This eliminates Python-level `__setattr__` overhead on every VDOM node attribute write while keeping Python `@property` setters (such as `_parent`) functional and preserving `SignalReceivable`'s default `__setattr__` behavior on non-element subclasses (`Receiver(SignalReceivable)`).

**Alternative considered:** Replacing `self.<attr> = ...` with `object.__setattr__` only on the six identified classes. Rejected because any future element or attribute storing a caller signal would reintroduce the same silent destruction bug.

### 2. Single-owner `_OwnedComputed` claiming (`_claim_owned_computed`)

Template helpers (`_holes.resolve_attr`, `_holes.resolve_var`, `_binder.bind_text_part`, `_binder.bind_for`, `bind_if`, `_markdown_for`, radio `_bind`, `MultiLineTextElement`) construct `_OwnedComputed` instances. Because an `_OwnedComputed` passed as a component prop (`<Child title="Hi {{ name }}" />` or `:items="box.items"`) can flow down into an inner `TextElement` or `SwitchElement` inside `Child`'s template, inner elements must not claim an already-claimed `_OwnedComputed`.

- Add `_claimed: bool = False` on `_OwnedComputed` and helper `_claim_owned_computed(owner: SignalReceivable, name: str, value: Any)`.
- `_bind_component_tag` marks unowned `_OwnedComputed` props as `_claimed = True` *before* calling `generator(props, slots=slots)` so synchronous setup inside the child component cannot let inner elements steal ownership; once `generator` returns the `Component`, `_bind_component_tag` registers those computeds on the `Component` via `__set_signal_member__(f"__prop_{k}", v)` (and cleans them up with `consumer_destroy()` if `generator` raises).
- In `Component._init_component` (`generator is None` path used by `AppDocumentRoot`), transfer any already-claimed entries in `node.__signal_members__` directly onto `self` and clear `node.__signal_members__`, avoiding double-claiming or ownership loss when the root `Element` is absorbed.

### 3. Uniform `_OwnedComputed` and explicit registration for internal signals

- Convert remaining internal derived computations that are passed into elements (`bind_text_part`, `bind_for`, `MultiLineTextElement`, `_expand_radio_bind`) from plain `Computed` to `_OwnedComputed` so their receiving elements claim and clean them up automatically.
- Register non-`Computed` / non-passed internal element computeds explicitly with `self.__set_signal_member__`: `_DictValueRow._token`, `TypedRouterLink._class_attr` & `_aria_current_attr`, `RouterView._level_match`.
- Guard `MarkdownForElement._on_set_parent` with `self._iterable_resolved` so reparenting does not allocate and leak duplicate `_OwnedComputed` instances.
- Clear `self._callback_nodes` in `ElementAbstract._remove_element` and `self._event_handlers_added` in `ElementBase._remove_element`.

## Risks / Trade-offs

- **Custom third-party `Component` attributes**: A `Component` that assigns `self.foo = Signal(...)` directly as a Python attribute on `self` (an obsolete class-component pattern) no longer populates `__signal_members__` implicitly. → Mitigation: `Component` composables (`use_state`, `use_reactive_list`, `use_reactive_dict`) already register explicitly via `_merge_transferables`, and `@computed_property` already calls `__set_signal_member__` directly; documented clearly in the `reactive` and `elements` specs.
