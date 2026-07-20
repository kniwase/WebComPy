## Context

WebComPy's scoped_style system processes CSS as nested Python dicts (`StyleDict`). The `ComponentGenerator.scoped_style` setter and `ReactiveScopedStyle` both use `_process_style_declaration`, `_classify_nested_key`, `_scope_combinator_selector`, and `_generate_css_recursive` helpers (defined in `_generator.py`) to produce scoped CSS strings. The dict structure maps CSS constructs as follows:

- Property declarations: `"property": "value"` (str value)
- Pseudo-classes/elements: `":hover": { nested }` (dict value, `:` prefix)
- At-rules: `"@media (...)": { nested }` (dict value, `@` prefix)
- Combinator selectors: `"sub-selector": { nested }` (dict value, other prefix)
- At-rule detection: `key.startswith("@")` → `_classify_nested_key` returns `"at-rule"`
- Pseudo detection: `key.startswith(":")` → returns `"pseudo"`
- Other nested keys → `"combinator"` (including `@keyframes` percentage selectors like `0%`)

This change introduces a CSS text parser that produces identical `StyleDict` structures from CSS text strings, enabling developers to write CSS in its natural form while reusing all existing scoping logic.

## Goals / Non-Goals

**Goals:**
- Parse CSS text strings into `StyleDict` structures matching the existing dict format
- Support all CSS constructs handled by WebComPy's scoped_style system
- Support `{{ varname }}` interpolation in reactive CSS via `css_text_template`
- File-based CSS loading via composition with `webcompy.resources.load_text` (async)
- All scoped_style assignment goes through explicit `css_text()` / `css_text_template()` calls

**Non-Goals:**
- Direct string assignment to `scoped_style` setter (must use `css_text()`)
- Modification of `ReactiveScopedStyle` or `ComponentGenerator` internals
- CSS validation/linting
- Sass/Less/CSS-in-JS
- `{{ }}` support in static scoped_style (no component context available at module level)

## Decisions

### D1: CSS text → StyleDict conversion, not direct CSS scoping

The CSS parser produces `StyleDict` (nested dict) rather than applying scoping directly to CSS text. This reuses all existing `_process_style_declaration`, `_classify_nested_key`, `_scope_combinator_selector`, and `_generate_css_recursive` logic without duplication.

**Rationale**: The existing dict-based scoping logic is tested and handles all edge cases (combinator splitting, pseudo-scoping, at-rule scoping, `@keyframes` special-casing). Producing `StyleDict` means the parser only needs to handle CSS structural parsing, not scoping semantics.

**Alternatives considered**: Directly inserting `[webcompy-cid-{id}]` into CSS text would require reimplementing the combinator split logic and would duplicate at-rule/pseudo/combinator classification.

### D2: Parenthesis-aware tokenizer for at-rule arguments

The CSS parser uses parenthesis-depth tracking when scanning for delimiters (`:`, `{`, `;`). This prevents `:` inside `@media (max-width: 768px)` from being misidentified as a property declaration.

**Rationale**: Without depth tracking, `max-width: 768px` would split at `:`, breaking the at-rule key. The parser tracks `(`/`)` depth and only considers delimiters at depth 0.

### D3: `{{ }}` resolution before CSS parsing

`css_text_template` resolves `{{ }}` holes in CSS text BEFORE parsing. The resolution uses `resolve_holes` from the shared `_holes.py` module (Change 1).

**Rationale**: CSS `{` and `}` are single braces, while `{{ }}` uses double braces. Resolving `{{ }}` first means the CSS parser never sees double braces — it only sees single braces in their structural role. This mirrors Jinja2's approach to CSS templating.

**Reactive integration path**: The factory function returned by `css_text_template(source, context)` SHALL be a `Callable[[], dict[str, StyleDict]]`. When called, it:
1. Reads the current values of all Signal dependencies (via `resolve_holes` — which reads Signal `.value` at call time).
2. Outputs the fully-resolved CSS text string.
3. Parses the string via the CSS parser and returns the resulting `StyleDict` dict.

This factory SHALL be passed as the argument to `reactive_scoped_style(factory)`. The existing `ReactiveScopedStyle` mechanism wraps the factory in a `Computed(lambda: factory())`. When `_render_css()` evaluates this `Computed`, the factory is called, `resolve_holes` reads Signal `.value` inside the `Computed` closure, and dependency tracking is automatically established. Signal changes dirty the `Computed`, which triggers `_render_css()` re-evaluation through the existing `on_after_updating` callback registered by `ReactiveScopedStyle`.

**Important**: The factory SHALL NOT internally create a `Computed`. All reactivity is achieved through `ReactiveScopedStyle`'s existing `Computed` wrapping of the passed factory.

### D4: Minimal type-level core modification

`css_text()` returns `dict[str, StyleDict]` which matches the existing `scoped_style` setter parameter type (`_generator.py:253`). `css_text_template()` returns `Callable[[], dict[str, StyleDict]]`, which SHALL be directly assignable to `reactive_scoped_style`'s `ReactiveScopedStyleFunc`.

To make this work, the existing `ReactiveScopedStyleFunc` type alias (`_reactive_scoped_style.py:61`) SHALL be corrected from `Callable[[], StyleDict]` to `Callable[[], dict[str, StyleDict]]`. The runtime contract of `render_css()` / `_apply_scope()` iterates `.items()` over the factory return value (`_reactive_scoped_style.py:174,214`), expecting a selector-keyed top-level dict (`dict[str, StyleDict]`), not a bare `StyleDict`. The current alias is a pre-existing type imprecision. No behavioral change — `render_css` and `_apply_scope` are unchanged.

**Rationale**: The user requires explicit `css_text()`/`css_text_template()` calls. Fixing the type alias ensures `css_text_template`'s return type is directly assignable to `ReactiveScopedStyleFunc`, avoiding casts at usage sites. This is a type-only change (one line, no behavioral impact).

### D5: Reuse `_holes.py` for `{{ }}` resolution

The `resolve_holes`, `split_text`, `HOLE_PATTERN`, and `resolve_var` utilities are defined in Change 1's `webcompy/template/_holes.py` shared module. `css_text_template` imports from this module. File-based CSS loading is delegated to `webcompy.resources.load_text` (Change 4). Callers compose `css_text(await load_text(path))` inside an async component setup function.

**Rationale**: Avoids duplicating the `{{ }}` resolution logic. Change 1's design is updated to include `_holes.py` extraction.

### D6: `str`-only signatures; file loading via composition with `load_text`

`css_text(source: str)` and `css_text_template(source: str, context: dict)` accept `str` only. File-based CSS loading is delegated to `webcompy.resources.load_text` (Change 4), which is async. Callers compose:

```python
@define_component
async def Card(ctx):
    css_src = await load_text("styles/card.css")
    style = css_text(css_src)
    return html.DIV(...)
```

**Rationale**: `css_text_template` returns a sync `Callable[[], dict[str, StyleDict]]` factory wrapped in a `Computed` by `reactive_scoped_style`. Since `Computed` evaluation is synchronous, the factory cannot call `await load_text(...)`. Therefore, file loading MUST happen outside the factory — before `css_text_template` is called. Dropping `Path` from both `css_text` and `css_text_template` (for API consistency) makes this constraint explicit at the type level.

**Browser behavior**: Unlike the originally planned `_load_file` (which would have raised `WebComPyException` in browser), `load_text` works in both server and browser. Server-side reads are recorded by `ServerResourcePort` and embedded in the hydration payload; browser-side reads resolve from the payload first (no fetch needed for resources read during SSR).

## Risks / Trade-offs

- **[Risk] CSS parser misses edge cases (CSS variables, vendor prefixes, complex selectors)** → Mitigation: Parser returns dict structure; properties and selectors are stored as raw strings. The existing `_process_style_declaration` handles value cleanup. Unknown constructs are preserved as-is.
- **[Risk] Performance of parsing CSS text on every reactive evaluation** → Mitigation: For static CSS, parsing happens once (module level). For reactive CSS, the `Computed` only re-evaluates on Signal change. The parser operates on small CSS blocks (typical component styles are <50 lines).
- **[Constraint] File-based CSS loading requires async context** → `load_text` is async (`await` inside async component setup). `css_text` and `css_text_template` accept `str` only — file loading is the caller's responsibility. This keeps the CSS parser pure (no I/O) and enables browser-side loading via the hydration payload (the originally planned browser-rejection no longer applies).
- **[Trade-off] No validation/error reporting on CSS syntax** → Acceptable — the parser is lenient (like HTMLParser). Invalid CSS produces incorrect dicts which produce incorrect scoped CSS. Developers can validate with external tools.

## Open Questions

None — all design decisions resolved during planning phase.
