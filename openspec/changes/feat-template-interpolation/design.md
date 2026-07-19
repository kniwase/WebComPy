## Context

WebComPy currently requires developers to define component templates via Python API calls (`html.DIV({...}, ...)`). This is verbose for simple structures and unfamiliar to web developers who expect to write HTML. The framework has no HTML parsing or template engine infrastructure.

The existing element system handles reactivity through direct type-based dispatch: `TextElement` accepts `SignalBase` for reactive text, `ElementBase._init_new_node` registers `on_after_updating` callbacks for Signal-valued attributes, and `_create_child_element` wraps `str`/`SignalBase` children into `TextElement`. A template engine can leverage these existing mechanisms by producing Element trees with the same type semantics.

Key constraints:
- No external dependencies (stdlib only) — must use `html.parser.HTMLParser`
- Must work in both server (standard Python) and browser (PyScript/Emscripten) environments
- Must produce `Element` instances (not strings), preserving Signal reactivity
- Root template must be a single `Element` (enforced by `Component.__init_component`)

## Goals / Non-Goals

**Goals:**
- Parse HTML template strings into WebComPy Element trees using stdlib `html.parser.HTMLParser`
- Support `{{ varname }}` interpolation in text content — Signal values passed through for reactive updates
- Support `{{ varname }}` interpolation in attribute values — Signals produce reactive `Computed` values, non-Signals produce static strings
- Support dot notation `{{ a.b.c }}` for dict/attribute access
- Support `@event="handler_var"` for event handler binding
- Support `:ref="ref_var"` for DomNodeRef binding
- Accept `locals()` or explicit dict as variable context
- Cache compiled Template ASTs per template string
- Reject `<script>`, `<style>`, and other CDATA elements for security
- Handle void elements (`<br>`, `<img>`, `<input>`, etc.), boolean attributes, and HTML comments
- Enforce single root element with whitespace trimming

**Non-Goals:**
- Control flow blocks (`{% if %}`, `{% for %}`) — deferred to Change 2
- File-based template loading (`Path` argument) — deferred to Change 4
- Component tag resolution (`<my-component>`) — deferred to Change 3
- Expression evaluation (`{{ x + y }}`, filters, etc.) — variable name reference only
- Template inheritance or includes

## Decisions

### D1: Use `html.parser.HTMLParser` with `convert_charrefs=True`

**Rationale**: `HTMLParser` is the only stdlib HTML parser with real-world HTML tolerance. `xml.etree.ElementTree` and `xml.dom.minidom` require well-formed XML and reject common HTML patterns (unclosed `<br>`, boolean attributes, etc.). `convert_charrefs=True` (default since Python 3.5) pre-resolves HTML entities, simplifying downstream processing.

**Alternatives considered**: `string.Template` and `string.Formatter` cannot parse HTML structure (flat text only). External libraries (Jinja2, lxml, BeautifulSoup) violate the no-dependency constraint.

### D2: Two-phase processing: Compile (parse → AST) then Bind (AST + context → Element tree)

**Rationale**: Separating parsing from binding enables caching of Template ASTs. The AST is immutable per template string and can be reused across multiple component renderings. The bind phase is context-dependent and runs per component setup.

**Shared pipeline**: A `_render_nodes(source, context: Mapping[str, Any] | None = None) -> list[ElementChildren]` function SHALL be exposed for internal reuse. Both `_render_nodes` and `render_template` SHALL reside in `template/__init__.py`. This function performs dedent → cache → parse → bind without single-root validation, returning all root nodes as a list. `render_template` wraps `_render_nodes` with the single-root `Element` assertion. This enables `render_markdown` (Change 6) to reuse the parser and binder while handling multi-root Markdown documents.

`ElementChildren = ElementAbstract | SignalBase | str | None` (existing TypeAlias in `webcompy/elements/typealias/_element_property.py`) is used in preference to `ElementAbstract` because text-only roots in `_render_nodes` legitimately produce `str` children that `_create_child_element` later wraps in `TextElement` — using the narrower `ElementAbstract` would have required an artificial Element wrapper for text fragments.

**Shared `_holes.py` module**: The interpolation utilities — `HOLE_PATTERN` regex, `LiteralText`/`Hole` dataclasses, `split_text()`, `resolve_var()`, and `resolve_holes()` — SHALL reside in `webcompy/template/_holes.py`. This module has no imports from other template modules (avoids circular dependencies) and is shared by `_ast.py` (text splitting), `_binder.py` (variable resolution), and Change 5's CSS text pipeline (`css_text_template`). `_ast.py` imports `LiteralText` and `Hole` from `_holes.py` to define `TemplateText`.

### D3: Signal objects passed through directly to `TextElement` for text interpolation

**Rationale**: `TextElement.__init__` already handles `SignalBase` by registering an `on_after_updating` callback. Passing the Signal object directly (rather than extracting `.value`) preserves reactivity. Non-Signal values (str, int, Element instances) are handled by `_create_child_element`'s existing type-based dispatch.

### D4: Reactive attribute evaluation via `Computed` for Signal-valued attributes

When one or more `{{ }}` holes in an attribute value reference a `SignalBase`, a `Computed` SHALL be generated that produces the full attribute string reactively. The `Computed` closure captures the resolved variable references from the context at bind time, and the `Computed`'s dependency tracking automatically picks up Signal references. The `Computed` is passed as the attribute value to `Element`, leveraging the existing `_init_new_node` / `_generate_attr_updater` mechanism for reactive DOM attribute updates.

When no Signal is referenced in the attribute holes, static string evaluation SHALL be used (no `Computed` created).

**Rationale**: The existing element system already supports reactive attributes: `ElementBase._init_new_node` checks `isinstance(value, SignalBase)` and registers `on_after_updating` callbacks. By returning a `Computed` signal instead of a plain string, the template engine leverages this built-in mechanism without any element system changes.

**API choice**: The template engine SHALL use `Computed(fn)` from `webcompy.signal` (Tier 2 — Internal constructor API) rather than `use_computed()` from `webcompy` top-level (Tier 1 — Public composable API). This follows the two-tier API defined in `composables/spec.md:64-81`: the template engine is framework infrastructure, not user-facing component setup code. `Computed()` does not emit warnings, does not participate in SSR transfer (derived values recompute on the browser), and is the correct API for framework-internal signal creation.

**Signal detection**: Before creating a `Computed`, all `{{ }}` holes are checked: if any resolved variable is a `SignalBase`, the `Computed` path is taken. If none are Signals, the static path is used. This avoids unnecessary `Computed` object creation for purely static attributes (common case).

### D5: Reject `<script>`, `<style>`, and CDATA elements

**Rationale**: HTMLParser treats these as CDATA content elements, delivering their entire content as a single `handle_data` blob. This bypasses the template engine's interpolation scanning. Additionally, `<script>` poses XSS risks and `<style>` poses CSS injection risks. WebComPy provides `scoped_style` for component CSS and `raw_html()` for controlled raw HTML insertion.

### D6: Void element tracking and `<br>` special-casing

**Rationale**: `HTMLParser` does NOT auto-close void elements — it calls `handle_starttag` without a matching `handle_endtag`. The tree builder must maintain a `VOID_ELEMENTS` set to avoid pushing void elements onto the element stack. `<br>` receives special treatment (`NewLine()` instead of `Element("br")`) because `"br"` is not a valid `HtmlTags` literal in WebComPy.

**Tag name type casting**: Since `Element.__init__` and `create_element` accept `tag_name: HtmlTags` (a `Literal[...]`), the binder SHALL cast parsed tag names via `cast("HtmlTags", tag_name)` for all element creation. This is consistent with `Element.__init__`'s own internal cast (`cast("HtmlTags", tag_name.lower())` at `_element.py:164`). The cast is safe: the HTML parser produces syntactically valid tag names, and `Element.__init__` already accepts arbitrary strings at runtime.

### Regex: HOLE_PATTERN

Variable interpolation holes SHALL be matched by:

```python
HOLE_PATTERN = re.compile(r"\{\{\s*([a-zA-Z_]\w*(?:\.[a-zA-Z_]\w*)*)\s*\}\}")
```

Each path segment MUST start with a letter or underscore (`[a-zA-Z_]`) followed by zero or more word characters (`\w*`), matching Python identifier rules. This rejects `{{123}}` (digit-first), `{{}}` (empty), and `{{` without closing `}}` as literal text — they will not be captured by the pattern. The group captures the full dot-notation path (e.g., `"user.name"` from `{{ user.name }}`) for resolution via `resolve_var`.

### D7: `textwrap.dedent` for indented triple-quoted strings

**Rationale**: Triple-quoted template strings from Python source have common leading whitespace. `textwrap.dedent` removes this without affecting template structure. Leading/trailing whitespace-only text nodes around the root element are stripped.

### D8: Explicit fail-fast validation for event/ref bindings and None attribute rendering

**`{{ }}` interpolation in `@event` and `:ref`**: Event handler names and ref variable names are static identifiers resolved at bind time; interpolation adds dynamic resolution complexity without benefit (events and refs are typically static component-level wiring). Rejecting `{{ }}` in these attributes at bind time gives clear feedback (`WebComPyException`) instead of confusing downstream errors (e.g., `KeyError` for an empty variable name caused by `_attr_text` silently dropping Hole parts).

**Non-callable event handler**: Bind-time `callable()` validation fails fast with `WebComPyException` listing the handler name and observed type, instead of producing a `TypeError` at the first event dispatch (which surfaces deep inside the event loop and obscures the root cause).

**None attribute hole**: The shared `format_value` helper (used by `resolve_holes` for CSS text and by `resolve_attr` for attributes via the unified `_render_parts` path) renders `None` as `""` consistently — including `Signal(None)` whose `.value` is `None`. The text path retains the spec-mandated "nothing inserted" semantics (handled separately in `bind_text_part`); the attribute path renders as empty string for both static and `Computed` paths. This eliminates `str(None)` → `"None"` leaking into DOM attributes and unifies formatting across the three interpolation consumers (text attribute static / attribute Computed / CSS `resolve_holes`).

`format_value` is exported via `webcompy.template.__all__` so that Change 5 (`css_text_template`) and other downstream consumers can import the shared formatter without reaching into `_holes.py` directly.

## Risks / Trade-offs

- **[Risk] HTMLParser may behave differently in PyScript** → Verified: the `template` E2E group exercises `render_template` end-to-end in the browser (PyScript/Pyodide) under both `prod` and `static` serving modes. Structure rendering, Signal-driven text updates, void/boolean attributes, and SSG HTML output all pass, confirming `html.parser.HTMLParser` behaves identically to standard Python in the Emscripten runtime.
- **[Risk] Template parse errors produce confusing messages** → Mitigation: Catch `HTMLParser` exceptions and re-raise with template-source context (line numbers if available).
- **[Risk] Large templates with many `{{ }}` holes may have performance impact** → Mitigation: `_create_child_element` and `TextElement` construction are O(1). The compile cache eliminates re-parsing cost. No virtual DOM diffing — direct updates only.
- **[Risk] Computed lifecycle management for reactive attributes** → Mitigation: The `Computed` is passed as an attribute value to an `Element`, which registers an `on_after_updating` consumer callback. When the Element is destroyed (`_remove_element` → `consumer_destroy` on callback nodes), the downstream consumer edge is cleaned up. The `Computed` itself becomes garbage-collectable when the Element is GC'd. This is the same lifecycle path as any user-provided `SignalBase`-valued attribute; no new cleanup mechanism is needed.
- **[Note] `locals()` captures `ctx` (ComponentContext) and all local variables** → When `locals()` is used as the context, the component's `ctx` parameter and any framework-injected locals become accessible from the template (e.g., `{{ ctx }}`). This is not dangerous — `TextElement` safely converts to string — but developers should be aware that the entire local scope is exposed. Explicit dicts can be used instead for tighter control.
- **[Note] Module-level `_template_cache` is bounded by an LRU policy** → The cache (`_cache.py`) stores compiled ASTs keyed by normalized source string in an `OrderedDict` capped at `_TEMPLATE_CACHE_MAX_SIZE = 128` entries. Cache hits call `move_to_end()` to record recent use; insertions that exceed the cap evict the least-recently-used entry via `popitem(last=False)`. This protects long-running workloads that generate many distinct dynamic templates while keeping the common case (compile-time constant templates) on the hot path. `clear_cache()` remains available for tests.

## Open Questions

None — all design decisions resolved during planning phase.
