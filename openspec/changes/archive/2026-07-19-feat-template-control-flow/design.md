## Context

Change 1 provides HTML parsing and `{{ }}` interpolation. This change adds control flow blocks (`{% if %}`, `{% for %}`) using Jinja2-compatible syntax. The key challenge is mapping these block constructs to WebComPy's reactive primitives (`switch()`, `repeat()`) while supporting multiple child elements per branch/iteration.

HTMLParser treats `{% %}` directives as plain text data, interleaved with HTML element events. The template engine must scan text nodes for `{% %}` patterns, split them into directive tokens, and restructure the flat element tree into control flow AST nodes (IfNode, ForNode).

The existing `switch()` and `repeat()` functions each expect single-child returns from their generators. To support multiple children per branch/iteration (common in Jinja2 templates), we introduce `FragmentElement` — a minimal `DynamicElement` that transparently renders multiple children without a DOM wrapper.

## Goals / Non-Goals

**Goals:**
- Parse `{% if %}`, `{% elif %}`, `{% else %}`, `{% endif %}` into conditional AST nodes
- Parse `{% for item in items %}`, `{% endfor %}` into loop AST nodes
- Map reactive Signal conditions to `switch()` (reactive DOM updates)
- Map static (non-Signal) conditions to truthiness evaluation at bind time
- Map `ReactiveList`/`ReactiveDict` iterables to `repeat()` (reactive DOM updates)
- Map plain `list`/`dict` iterables to list comprehension (static)
- Support multiple children per branch/iteration via `FragmentElement`
- Support nested control flow (if inside for, for inside if)
- Support dot notation in conditions and iterable references

**Non-Goals:**
- `{% else %}` within `{% for %}` (empty-iterable fallback)
- Expression evaluation in conditions (`{% if x > 0 %}`) — variable reference only
- `{% extends %}`, `{% block %}`, `{% include %}` — component system handles composition
- `{# comment #}` syntax — HTML comments already supported
- `{% set %}`, `{% macro %}`, filters (`|`)

## Decisions

### D1: FragmentElement — transparent DynamicElement wrapper

`FragmentElement(DynamicElement)` holds a list of children and renders them directly in the parent DOM without a wrapper element. It leverages `DynamicElement._render()` which already positions children sequentially and `DynamicElement._node_count` which sums child counts.

**Rationale**: Both `switch()` and `repeat()` require single-child returns from generators. FragmentElement wraps multiple children into a single `ElementChildren`-compatible value. Existing `_position_element_nodes` and `_render` infrastructure handles positioning correctly.

**Note**: The class hierarchy is `DynamicElement → ElementWithChildren → ElementAbstract`, NOT `ElementBase` (which extends `ElementWithChildren` as a sibling of `DynamicElement`). The `refactor-element-foundations` change widens the child-node type alias from `ElementBase`-based to `ElementAbstract`-based, making `FragmentElement` (and `SwitchElement` / `RepeatElement` / `MultiLineTextElement`) automatically valid as `ElementChildren` without a per-element type-alias addition. The FragmentElement implementation does not need its own `ElementChildren` edit.

**Alternatives considered**: Extending `repeat()` API for multi-child returns would add ~5 new overloads. Creating entirely new element types (TemplateIfElement, TemplateForElement) would duplicate `SwitchElement`/`RepeatElement` behavior (~200+ lines each).

### Regex: DIRECTIVE_PATTERN

Control flow directives SHALL be matched by:

```python
DIRECTIVE_PATTERN = re.compile(
    r"\{%\s*(?P<directive>if|elif|else|endif|for|endfor)\b(?P<args>[^%]*)%\}"
)
```

Directive argument parsing:
- `if`/`elif`: args = variable path (e.g., `show`, `item.visible`)
- `for`: args = `item in items` or `key, value in items` — split on ` in ` to extract left-hand side and iterable_path; if left-hand side contains `,`, the loop variables are unpacked as a tuple (e.g., `["key", "value"]`)
- `else`/`endif`/`endfor`: no args
The `[^%]*` capture group includes leading/trailing whitespace (e.g., `" show "` for `{% if show %}`). The extracted args SHALL be `.strip()`ed before further processing.

### D2: Two-phase parsing for {% %} blocks

Phase 1: HTMLParser builds element tree (same as Change 1). Phase 2: Text nodes are scanned for `{% %}` patterns, split into directive tokens and literal text. Phase 3: Bracket matching groups directive tokens with their children into IfNode/ForNode AST nodes.

**Rationale**: HTMLParser treats `{% %}` as text. Post-processing the element tree is simpler than modifying HTMLParser's event stream. Bracket matching naturally handles nesting (if inside for, etc.).

### D3: Signal detection for reactive vs static dispatch

`bind_if` and `bind_for` inspect resolved values at bind time. If any condition or iterable is a `SignalBase`, the reactive path (`switch()`/`repeat()`) is taken. Otherwise, static evaluation is performed.

**Rationale**: Single code path per call. The detection is O(n) where n is the number of branches/iterations — negligible. No special syntax needed for reactive vs static — it's automatic based on variable type.

### D4: Multi-child in for body — FragmentElement for reactive, list extension for static

For reactive `{% for %}`, each iteration's body children are wrapped in `FragmentElement` (if >1) and passed to `repeat()`. For static, children are appended directly to the parent's children list.

**Rationale**: `repeat()` requires single `ElementChildren` return. FragmentElement satisfies this for the reactive case. For static, direct append avoids the overhead of FragmentElement creation.

### D5: Dot notation in conditions and iterables

The same `resolve_var` function from Change 1 handles dot notation in `{% if item.visible %}` and `{% for item in user.posts %}`.

**Rationale**: Consistency with `{{ }}` interpolation. No new parsing or resolution infrastructure needed.

### D6: Dict key-value unpacking in {% for %}

When the for directive's left-hand side contains a comma (e.g., `{% for key, value in my_dict %}`), the loop variables are split into a tuple and the `repeat()` overload `Callable[[V, K], ElementChildren]` is used. The `repeat()` callback receives `(value, key)` in that order (matching the `RepeatElement` signature). The binder maps template variable names by position: `key` → `callback_arg[1]`, `value` → `callback_arg[0]`, and both are added to the per-iteration context.

**Rationale**: The `repeat()` function already supports dict iteration with key access via the `Callable[[V, K], ElementChildren]` overload. Adding tuple unpacking in the template syntax surfaces this capability without new element types. Single-variable `{% for value in dict %}` uses the existing `Callable[[V], ElementChildren]` overload.

### D7: Mixed Signal and plain values in if-elif chains

When an `{% if %}` / `{% elif %}` chain contains a mix of Signal and plain value conditions (e.g., `{% if signal_a %}A{% elif plain_bool %}B{% endif %}`), the presence of any Signal triggers the reactive path (`switch()`). `SwitchElement._select_generator()` already handles mixed types at runtime — it calls `isinstance(cond, SignalBase)` to decide `.value` extraction vs. direct `truth()` evaluation, and registers `on_after_updating` callbacks only for Signal conditions.

To support mixed-type conditions, `SwitchCasesSignal` (`_switch.py:23`) SHALL be widened from `list[tuple[SignalBase[Any], NodeGenerator]]` to `list[tuple[Any, NodeGenerator]]`. This makes the type alias match the runtime contract in `_select_generator()` (which casts to `list[tuple[SignalBase[Any] | Any, NodeGenerator]]` at `_switch.py:44`). It also achieves consistency with `SwitchCasesSignalList` (`_switch.py:24`), which already uses `Any` for conditions. The public `switch()` function still enforces `SignalBase` via the `SwitchCase` TypedDict (`generators.py:113-115`), so the public API contract is preserved.

**Rationale**: The type alias was narrower than the runtime contract — `_select_generator()` already handles non-Signal conditions via `isinstance`. Widening aligns the type with actual behavior and avoids a `cast()` in binder code. No behavioral change; pure type-level fix.

## Risks / Trade-offs

- **[Risk] `{% %}` bracket matching fails on malformed templates** → Mitigation: Raise clear error with line context. Jinja2 also errors on unmatched `{% %}` blocks.
- **[Risk] Whitespace around `{% %}` produces extra text nodes** → Mitigation: Browser normalizes whitespace; no visual impact. Jinja2's `trim_blocks` equivalent can be added later.
- **[Risk] FragmentElement in `_is_patchable` returns False (DynamicElements are never patchable)** → Mitigation: Non-patchable means full redraw, which is expected for conditional branches. No correctness impact.
- **[Risk] FragmentElement with 0 children** → Mitigation: 0-children case is valid (empty branch). `DynamicElement._render()` handles empty `_children` gracefully.

## Open Questions

None — all design decisions resolved during planning phase.
