# Design: Reactive Scoped Style

## Overview

```
┌──────────────────────────────────────────────────────────────────────────┐
│ User code                                                                │
│                                                                          │
│   @define_component                                                      │
│   def MyComponent(context):                                              │
│       color = Signal("blue")                                             │
│       context.use_reactive_scoped_style(                                 │
│           reactive_scoped_style(lambda: {                                │
│               ".my-class": {"color": color.value},                       │
│           })                                                             │
│       )                                                                  │
│       return html.DIV({}, "...")                                         │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ Framework internal                                                       │
│                                                                          │
│   ReactiveScopedStyle                                                    │
│     ├ _func: Callable[[], dict]                                          │
│     ├ _dict_computed: Computed[dict]   ← wraps _func                     │
│     └ _css_computed: Computed[str]    ← _dict_computed + render + scope │
│                                                                          │
│   ComponentGenerator                                                     │
│     └ _reactive_styles: list[ReactiveScopedStyle]                        │
│                                                                          │
│   HeadElement._render()                                                  │
│     ├ for each gen in store:                                             │
│     │   for each rx_style in gen._reactive_styles:                       │
│     │     create <style data-webcompy-cid-rx="{cid}-{idx}">              │
│     │     subscribe _css_computed.on_after_updating(                     │
│     │       lambda v: el.textContent = v                                 │
│     │     )                                                              │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

## Decisions

### Decision 1: Two Computeds (dict, str) — not one

The style function returns a dict. The rendered CSS is a string. Splitting into two Computeds lets:

- The dict Computed be inspected and re-used (e.g., for a future style-debugging tool that wants the raw dict)
- The CSS Computed's downstream `on_after_updating` callback only fires when the rendered string actually changes, not when the dict changes shape but renders identically

**Trade-off accepted:** Two Computeds means two subscriptions. Negligible cost.

### Decision 2: Distinct element attribute (`data-webcompy-cid-rx`) — not reuse `data-webcompy-cid`

The static `scoped_style` already uses `data-webcompy-cid="{cid}"`. A reactive style coexists with the static one. Distinguishing the attribute lets the framework:

- Reconcile each kind independently
- Allow a component to have both a static `scoped_style` AND a reactive style
- Inspect/clear reactive styles without affecting the static path

The attribute value format is `{cid}-{index}` where `index` is the position in the generator's `_reactive_styles` list. This guarantees uniqueness even if the same generator is re-instantiated (the cid is shared but the index disambiguates).

**Alternative rejected:** Reusing `data-webcompy-cid` and merging the static and reactive CSS into one element. This would couple the two systems and complicate textContent updates (would need to re-render the static portion too).

### Decision 3: Function-based primary API, class-based escape hatch

The primary API is a single function: `reactive_scoped_style(func)`. It returns a `ReactiveScopedStyle` instance. The class is exposed for advanced use cases (e.g., users who want to subclass and override `_render_css`).

```python
# Primary: function form
context.use_reactive_scoped_style(reactive_scoped_style(lambda: {...}))

# Advanced: class form
class MyStyle(ReactiveScopedStyle):
    def render_css(self, cid: str) -> str:
        return f"*[webcompy-cid-{cid}] {{ ... custom ... }}"
```

**Rationale:** The function form is the most common case. The class form is rare but available. Both register via the same `use_reactive_scoped_style` method.

### Decision 4: Multiple reactive styles per component — allowed, no upper bound

A component may register any number of reactive styles. Each becomes a separate `<style>` element. This lets users organize large style definitions (e.g., one for layout, one for color, one for typography) into logical groups.

**Trade-off accepted:** More `<style>` elements. Browsers handle thousands of style elements without issue; the practical limit is unrelated to this change.

### Decision 5: `use_reactive_scoped_style` is a method on `ComponentContext`, called from inside the component

The method lives on `ComponentContext` (already passed to every component setup function). It must be called before the component returns its template, so the framework can associate the style with the generator at the right time.

**Implementation detail:** `ComponentContext` already has access to the current component generator through the `context._generator` field (introduced in a previous change). We use this reference to look up the `ComponentGenerator` and append to its `_reactive_styles` list.

### Decision 6: Re-render on signal change updates the element's `textContent` — not innerHTML

The `<style>` element's `textContent` is set to the new CSS string. This is faster than `innerHTML`, avoids HTML-parser overhead, and matches the convention used elsewhere in `HeadElement`.

### Decision 7: Subscription cleanup is tied to the component lifecycle

`Component._remove_element()` and `Component._detach_from_node()` both call `on_before_destroy()`. The reactive style's `CallbackConsumerNode` is registered with the component's effect scope (via the `EffectScope` already created in `__setup()`), so it is automatically disposed when the component is destroyed. No manual cleanup is required.

### Decision 8: SSR initial value uses the current `Computed` value

During SSR (`get_head_content_html`), the framework calls `reactive_style.render_css(cid)`, which evaluates the `Computed` once and returns the resulting string. This value reflects the signals at SSR time. Hydration on the client uses the same mechanism, so the initial paint matches.

**Caveat:** If the cookie-based theme differs between SSR and client (e.g., the user changes their theme between the SSR render and the page load), there is a flash. This is the same flash the current `data-theme` approach has, and is out of scope here.

## Alternatives Considered

### A. Global `app.append_style(content: Computed[str])` — rejected

Would inject a single global `<style>` tag in `<head>`. Simpler, but doesn't address the user's stated need: "per-component scoped styling with signals".

### B. Reactive values inside the existing `scoped_style` dict — rejected

```python
MyComponent.scoped_style = {
    ".my-class": {
        "color": Computed(lambda: color_signal.value),  # ← Computed here
    }
}
```

Requires teaching `_process_style_declaration` (in `_generator.py`) to handle `Computed` values. The processing would need to be deferred (since the dict is set once at class definition time, the signal reference would be lost on re-evaluation). This is exactly the problem the user identified: "今のコンポーネント定義後に外から代入する感じではリアクティブにするのは難しそうです".

### C. Decorator form `@with_reactive_scoped_style(func)` — deferred

```python
@define_component
@with_reactive_scoped_style(lambda: {".x": {"color": "blue"}})
def MyComponent(context):
    ...
```

Cleaner, but: (1) the function is evaluated at class-definition time before the component body runs, so signals defined inside the body are not accessible; (2) the user said the function form is preferable because it works "inside the component definition". This is a future enhancement if the function form proves limiting.

### D. Replace static `scoped_style` with reactive — rejected

The static API is well-established, used in the framework's own components, and used by all current docs_app components. A replacement would be a breaking change with no clear benefit (the two systems coexist cleanly).

## File Layout

```
webcompy/components/
├── __init__.py                  # add reactive_scoped_style, ReactiveScopedStyle exports
├── _component.py                # (no change)
├── _generator.py                # add _reactive_styles attribute
├── _libs.py                     # ComponentContext gains use_reactive_scoped_style method
├── _reactive_scoped_style.py    # NEW: ReactiveScopedStyle class, reactive_scoped_style func
└── _hooks.py                    # (no change)

webcompy/elements/
└── _head.py                     # _render() + get_head_content_html() extended

tests/
└── test_reactive_scoped_style.py  # NEW

openspec/
├── changes/feat-reactive-scoped-style/
│   ├── proposal.md
│   ├── design.md (this file)
│   ├── tasks.md
│   └── specs/reactive-scoped-style/spec.md
```

## OpenSpec Spec Location

- `openspec/specs/reactive-scoped-style/spec.md` (synced from this change at archive time)
- `openspec/specs/components/spec.md` (modified: add `use_reactive_scoped_style` method to `ComponentContext`)

## Risk Analysis

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| `_reactive_styles` list grows unbounded if registered repeatedly | low | medium | The `use_reactive_scoped_style` is called inside the component setup, which runs once per component instance lifecycle. The list is on the generator (shared across instances), but typically registered styles are stable. Document that the call should be deterministic. |
| `Computed` re-evaluation cost on every signal change | medium | low | The CSS string is typically small (< 1KB). Recomputing on each change is O(n) where n is the number of declarations. Negligible in practice. |
| SSR/client hydration mismatch | low | low | Both paths use the same `Computed.value`. Initial paint matches. |
| `data-webcompy-cid-rx` selector collision with user CSS | low | low | The `data-webcompy-*` namespace is already reserved. No collision. |
| `use_reactive_scoped_style` called outside a component (e.g., from a non-component function) | low | medium | Detect via the active component context; raise a clear error. |
