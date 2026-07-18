## Why

After establishing the template interpolation foundation in Change 1, the next essential capability is control flow — conditionals and loops. Without `{% if %}` and `{% for %}`, templates are limited to static structure with data interpolation only. Any meaningful UI requires conditional rendering (show/hide elements) and iteration (lists, collections). These map naturally to Jinja2's `{% %}` block syntax, which Python web developers already know.

## What Changes

- Add `{% if var %}` / `{% elif var %}` / `{% else %}` / `{% endif %}` conditional blocks that map to `switch()` for reactive Signal conditions and static evaluation for plain values
- Add `{% for item in items %}` / `{% endfor %}` loop blocks that map to `repeat()` for `ReactiveList`/`ReactiveDict` and list comprehension for plain iterables
- Add `FragmentElement` — a minimal `DynamicElement` that renders multiple children transparently without a DOM wrapper, enabling multiple elements per branch/iteration. After `refactor-element-foundations`, `FragmentElement` (an `ElementAbstract` subclass) is automatically valid as `ElementChildren`; no separate type-alias edit is needed.
- Support dot notation (`item.visible`) in conditions and iterable references
- Support nested control flow (`{% if %}` inside `{% for %}` and vice versa)
- Support `{% elif %}` and `{% else %}` within `{% if %}` blocks

## Capabilities

### New Capabilities
_None — all capabilities extend `template-engine` from Change 1_

### Modified Capabilities
- `template-engine`: Added conditional and loop control flow blocks (`{% if %}`, `{% for %}`), FragmentElement for multi-child support

## Known Issues Addressed
_None — this is a new capability layered on Change 1_

## Non-goals
- `{% else %}` within `{% for %}` (empty-iterable fallback)
- Expression evaluation in conditions (`{% if x > 0 %}`) — variable reference only
- `{% extends %}`, `{% block %}`, `{% include %}` — component system handles composition
- `{# comment #}` syntax — HTML comments already supported

## Impact

- **New element**: `FragmentElement(DynamicElement)` in `webcompy/elements/types/_fragment.py`
- **Type-alias dependency**: Relies on `refactor-element-foundations` which widens the child-node type alias to `ElementAbstract`, making `FragmentElement` automatically valid as `ElementChildren` without a per-element addition
- **Modified files**: `template/_parser.py` (text splitting for `{% %}`), `template/_ast.py` (IfNode, ForNode), `template/_binder.py` (bind_if, bind_for), `elements/types/_switch.py` (`SwitchCasesSignal` type alias widened from `list[tuple[SignalBase[Any], NodeGenerator]]` to `list[tuple[Any, NodeGenerator]]` — type-only, no behavioral change)
- **Minimal element system change**: FragmentElement is a simple ~10 line DynamicElement subclass
- **No breaking changes**: Pure addition

## Dependencies

- **Depends on**: Change 1 (template interpolation — parser, binder, and AST infrastructure); `refactor-element-foundations` (FragmentElement relies on the child-node type alias being `ElementAbstract`-based)
- **Required by**: Change 3 (component tags — FragmentElement for multi-child slot wrapping), Change 6 (markdown — `{% if %}`/`{% for %}` blocks in Markdown templates), Change 7 (markdown for-expansion — `FragmentElement` for multi-child wrapping, for-loop AST structure)
- **Recommended implementation order**: Second template-engine change (0 → 1 → **2** → 3 → 4 → 5 → 6 → 7)
