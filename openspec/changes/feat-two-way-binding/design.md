# Design: `:bind` Two-Way Binding

## Context

**Goal of this document**: enable a fresh session (no prior context) to implement `:bind` correctly per intent. It records the exact interception points, code sketches, and the rationale behind each decision.

### Current pipeline (verified against origin/main @ 5f9c52d)

Two-way binding today is manual (`webcompy-cli/template_data/app/components/input.py:14-15`):

```python
def on_input(ev):
    assert ev.target is not None
    text.value = ev.target.value
html.INPUT({"value": text, "@input": on_input})
```

Relevant code paths:

1. **Element API**: `html.INPUT({...})` → `create_element()` (`packages/webcompy/src/webcompy/elements/generators.py:43`) splits the attribute dict: `@event`+callable → `events`, `:ref`+DomNodeRef → `ref`, `:preserve_children` → flag, **everything else (including a future `:bind`) → `attrs`**. It then calls `Element(tag_name, attrs, events, ref, children)` (`packages/webcompy/src/webcompy/elements/types/_element.py:154-170`).

2. **Signal→DOM reactivity (existing)**: `Element._init_new_node()` (`_element.py:86-103`) sets each attr via `setAttribute`, and for any attr whose value is `SignalBase`, registers `value.on_after_updating(self._generate_attr_updater(name))` (`_element.py:111-121`). So assigning a Signal as an attr value already gives one-way reactive updates for free — `:bind` reuses this.

3. **Event lifecycle (existing)**: handlers in `self._event_handlers` are wrapped by `_generate_event_handler()` (`_element.py:23-30`), which routes coroutine functions through `resolve_async` and wraps the handler via `inject(FFI_PORT_KEY).create_proxy(...)`. Cleanup: `_detach_from_node()` (`_element.py:123-148`) calls `removeEventListener` and `destroy()` on each proxy. **Framework invariant: all event handlers must go through this path** — `:bind` write-back handlers must be injected into `self._event_handlers`, never registered directly on nodes.

4. **Template path**: `bind_element()` (`packages/webcompy/src/webcompy/template/_binder.py:380-408`) calls `classify_attrs()` (`_binder.py:55-90`), which currently **rejects every `:`-prefixed attribute except `:ref`** with `WebComPyException` ("Unsupported attribute ':x' on HTML element: only ':ref' is allowed..."). `bind_element` then constructs `Element(tag_name=..., attrs=resolved_attrs, events=events, ref=ref, children=children)` directly (NOT via `create_element`).

5. **Writability**: `Signal` has a `value` setter (`packages/webcompy/src/webcompy/signal/_base.py:157`); `Computed` and `ReadonlySignal` (`packages/webcompy/src/webcompy/signal/_readonly.py:11-27`) are read-only; `ReactiveList`/`ReactiveDict` are container signals not meaningful as scalar binding targets.

6. **DOM event access**: handlers receive the raw event; existing code reads `ev.target.value` / `ev.target.checked` (see `e2e/core/my_app/pages/event.py:23`, template_data input.py). `ev.target` may be `None` — guard.

## Goals / Non-Goals

**Goals:**

- `html.INPUT({":bind": signal})` and `<input :bind="signal">` produce full two-way wiring for: text-like inputs, `textarea`, `input[type=number]`, `input[type=checkbox]`, `input[type=radio]`.
- Single interception point serving both the element API and the template path.
- Zero changes to the event-lifecycle and attr-reactivity machinery (reuse both).
- Descriptive `WebComPyException` for every misuse (wrong signal kind, wrong value type, conflicts, unsupported elements).
- SSR output identical in shape to hand-written equivalents (bound attr only; no events server-side).

**Non-Goals:**

- `<select>`/`<option>` (property-level `value` assignment and SSR `selected` handling; follow-up).
- `use_field`/validators/`use_form` (planned `feat-form-fields`; `:bind` accepting a Field object comes with that change).
- Dynamic `input[type]` combined with `:bind` (rejected, see D4).
- Component-tag `:bind` semantics (on components it stays an ordinary prop named `bind`).
- Update-timing selection for text-like bindings (commit on `change`/`blur` vs per-keystroke `input`; e.g. Vue `.lazy`, Blazor `@bind:event`, Angular `updateOn`). `:bind` on text-like inputs, number inputs, and textareas updates on every `input` event only. This matches the majority of JS reactive frameworks (Vue/Svelte/React/Angular/Solid default to per-keystroke; Blazor and Aurelia 1 default to commit). A commit-timing variant is deferred: validation timing will be addressed together with `feat-form-fields` (`use_field`), and a `:bind-event`-style extension can be added if needed. The existing skip policy for number inputs and the Signal same-value suppression already neutralize the two classic per-keystroke failure modes (intermediate unparseable values, signal→DOM echo).

## Decisions

### D1. Intercept `:bind` inside `Element.__init__` (single convergence point)

Both construction paths end at `Element.__init__` with `attrs: dict[str, AttrValue]`. `Element.__init__` (`_element.py:163-170`) currently does `self._attrs = attrs if attrs else dict()`. The interception pops `":bind"` from the incoming attrs and expands it into (a) a bound attr entry and (b) a write-back entry in `events` — before the dicts are stored. Because expansion happens in `__init__`, the existing `_init_new_node` attr-reactivity and event-proxy lifecycle apply unchanged, in browser, SSR, hydration, and TestRenderer paths.

**Alternative considered:** expanding in `create_element()` only — rejected: the template path (`bind_element`) constructs `Element` directly and would need duplicated logic.

**Alternative considered:** a new element subclass `BoundInputElement` — rejected: tag-generic behavior (input types, textarea) fits a pure expansion function better than an inheritance branch, and `_node_matches_existing`/hydration stay untouched.

### D2. Expansion logic lives in a new module `webcompy/elements/_bind.py`

New private module keeps `Element` slim and gives tests a direct unit surface:

```python
# packages/webcompy/src/webcompy/elements/_bind.py (sketch)
from webcompy.signal import Signal, SignalBase, Computed
from webcompy.exception import WebComPyException

_TEXT_TYPES = {"text", "email", "password", "search", "tel", "url"}

def expand_bind_attr(
    tag_name: str,
    attrs: dict[str, AttrValue],
    events: dict[str, EventHandler],
) -> None:
    """Pop ':bind' from attrs and expand it into a bound attr + write-back handler.

    Raises WebComPyException for: unsupported tag, non-Signal value, read-only
    signal kind, type-discipline violation, bound-attr conflict, dynamic type attr.
    """
```

`Element.__init__` calls `expand_bind_attr(self._tag_name, attrs, events)` before storing, when `":bind" in attrs`.

### D3. Per-element binding rules

Determination order: tag name first, then the **static** `type` attribute for `input`.

| Tag / type | Bound attr | Event | Signal→DOM | DOM→Signal |
|---|---|---|---|---|
| `input` with `type` in `_TEXT_TYPES` or absent | `value` | `input` | signal as attr (existing pipeline) | `signal.value = ev.target.value` |
| `textarea` | `value` | `input` | same | same |
| `input[type=number]` | `value` | `input` | same | converted per D5 |
| `input[type=checkbox]` | `checked` | `change` | signal as attr | `signal.value = bool(ev.target.checked)` |
| `input[type=radio]` | `checked` | `change` | `Computed(lambda: sig.value == radio_value)` | `if ev.target.checked: sig.value = radio_value` |
| anything else (incl. `select`, `option`) | — | — | error | error |

Radio `radio_value` = the element's **static** `value` attribute; missing or non-static `value` on a radio with `:bind` → `WebComPyException` ("radio :bind requires a static value attribute"). Multiple radios sharing one Signal form a group naturally.

### D4. Static-type requirement for `input`

Binding semantics depend on `type`. If `attrs["type"]` is a `SignalBase` (dynamic), `expand_bind_attr` raises: "`:bind` requires a static `type` attribute". A missing `type` defaults to text semantics (matches the HTML default).

### D5. Number conversion

Write-back for `input[type=number]`:

```python
def handler(ev):
    target = ev.target
    if target is None:
        return
    raw = target.value
    if raw == "":
        return                      # empty input: skip (documented)
    current = signal.value
    try:
        signal.value = int(raw) if isinstance(current, int) else float(raw)
    except ValueError:
        pass                        # unparseable: skip (documented)
```

Type chosen from the Signal's **current** value (`int` → `int()`, otherwise `float()`); `bool` is excluded by the type-discipline check (D6) even though `bool` is an `int` subclass.

**Alternative considered:** empty input sets `0`/`0.0` — rejected: silently overwriting user intent; skipping keeps the last valid value, matching native number-input behavior where `value` is "" while typing.

### D6. Type-discipline validation (at expansion time)

| Binding | Required Signal value type | Error if |
|---|---|---|
| text-like / textarea | `str` | otherwise |
| number | `int` or `float` (not `bool`) | otherwise |
| checkbox | `bool` | otherwise |
| radio | any (hashable compared by `==`) | — |

Signal kind check (before type check): value must be a `Signal` instance exactly — `Computed`, `ReadonlySignal`, `ReactiveList`, `ReactiveDict`, and plain non-signals raise `" :bind requires a writable Signal (got <type>)"`.

### D7. Conflict policy

- Bound-attr duplication: attrs already containing the bound name (`value` for text-like/number, `checked` for checkbox/radio) → `WebComPyException("':bind' conflicts with explicit '<name>' attribute")`. Silent precedence would be ambiguous; explicit error forces intent. (For radio, an explicit static `value` attr is REQUIRED and is not a conflict — `value` is not the bound attr there.)
- Same-event user handler: chained. Expansion wraps: `events["input"] = _chained(binding_handler, user_handler)` — binding first, then user handler, both through the existing single proxy path. Chaining preserves side-effect use cases (e.g., live-search hook) without forbidding composition. A user handler for a *different* event (e.g., `@blur`) is untouched.

### D8. Template `:bind` is resolved like `:ref`

In `classify_attrs()` (`_binder.py:55-90`), extend the `:`-branch: allow `":bind"` in addition to `":ref"`. Rules mirror `:ref`:

- No `{{ }}` holes inside the attribute value → `WebComPyException` (interpolation unsupported, like `:ref`).
- `resolve_var(raw_value, ctx)` must yield a `Signal` → otherwise `WebComPyException` naming the variable and observed type.
- The resolved Signal is passed into the Element via `resolved_attrs[":bind"] = signal` so template and element API converge on D1's interception.
- The error message for other `:`-prefixed attributes is updated to say "only ':ref' and ':bind' are allowed".

Component tags are untouched: `_bind_component_tag` treats `:bind` as a plain prop.

### D9. SSR and hydration need no new code

SSR renders `attrs` (bound attr with initial value) and ignores `events` — unchanged. Hydration: the bound attr updater re-registers and event proxies attach via the existing `_init_new_node`/`_adopt_node` paths — unchanged. The expansion is environment-agnostic; browser-only behavior is confined to the pre-existing event-proxy layer.

### D10. `:bind` on a `<select>` raises (documented deferral)

Select needs property-level `value` assignment (no `value` attribute semantics on `<select>`) and SSR-side `selected` on the matching `<option>`. Rather than half-supporting it, `:bind` on `select`/`option` raises "not supported (yet); bind a change handler manually". This keeps the change's surface honest.

## Risks / Trade-offs

- [Users expect `v-model`-style naming] → naming decision was made deliberately after comparing Svelte/Blazor/Aurelia (`bind`) vs Vue/Angular (`model`); documented in proposal.
- [Radio needs `Computed` per radio] → one lazy Computed per radio element; equality check suppresses redundant downstream updates; acceptable.
- [Chained handlers hide ordering bugs] → order is fixed (binding first) and documented in spec scenarios.
- [`:bind` in `attrs` dict leaks into `setAttribute` if expansion is missed] → expansion pops the key before storage; a unit test asserts no `:bind` attribute reaches the DOM.
- [Number skip-on-empty confuses users clearing a field] → documented behavior; form-fields change can add explicit clearing semantics later.

## Migration Plan

No breaking changes. Manual `value` + `@input` patterns keep working; `:bind` is additive. The CLI project template and docs demos can adopt `:bind` in a follow-up (not this change).

## Open Questions

None.
