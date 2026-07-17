## Context

Change 6's `render_markdown` pipeline converts Markdown to HTML via `MarkdownPort`, strips `<p>` wrappers around `{% %}` directives, then feeds the HTML to `_render_nodes` for template binding. `{% for %}` blocks in the HTML use standard `repeat()` — which renders the for-body per item independently. For Markdown-native list items (`- {{ item }}`), the Markdown parser generates a complete `<ul><li>{{ item }}</li></ul>` per list block, and `repeat()` stacks one `<ul>` per iteration instead of merging list items into a single `<ul>`.

The key insight: **merging Markdown list items across iterations requires rendering all items' markdown text together in one MarkdownPort pass.** Separately rendered subtrees cannot share a `<ul>` wrapper. A `DynamicElement` that concatenates per-item markdown, renders once, and re-renders on collection change solves this while preserving field-level reactivity.

## Goals / Non-Goals

**Goals:**
- Merge `{% for %}` over Markdown native list bodies into a single `<ul>` (or `<ol>`) with all `<li>` children
- Preserve field-level reactivity: `{{ item.field }}` where `item.field` is a Signal SHALL update fine-grained via `TextElement`, without triggering block re-render
- Support collection reactivity: when the iterable (e.g., `ReactiveList`) changes, re-render the merged block wholesale
- Detect list-body vs non-list-body for-loops and route accordingly: list → `MarkdownForElement`; non-list → repeat() (unchanged, fully reactive)
- Support nested `{% for %}`, tuple unpacking (`{% for k, v in d %}`), and per-item `{% if %}` (static evaluation)
- Follow `SwitchElement` lifecycle patterns for callback node management and async `_refresh`

**Non-Goals:**
- Reactive `{% if %}` inside a merging list-body `{% for %}` — the `{% if %}` is statically evaluated per item (fundamental constraint; use `<ul>{% for %}{% if %}<li>...</li>{% endif %}{% endfor %}</ul>` for reactive list-item conditionals).
- Incremental (O(1)) patching — block re-render on collection change is O(N), acceptable for content pages
- `{% else %}` within `{% for %}`
- General-purpose reactive-markdown primitive

## Decisions

### D1: `MarkdownForElement(DynamicElement)` — reactive block-rendering for loops

`MarkdownForElement` SHALL be a `DynamicElement` subclass in `webcompy/template/_markdown_for.py`. It holds the iterable, the body markdown template (string), the loop variable names (list of str), and the binding context. On render:

1. Read current items from the iterable (if `ReactiveList`/`ReactiveDict`, reading `.value`/iterating establishes reactive dependency).
2. For each item N, apply expression-scoped renaming to the body markdown: within `{{ }}`/`{% %}` spans, replace the loop variable name(s) with `__wmdf_{N}_{varname}`. Inject `__wmdf_N_varname = items[N]` into the context.
3. Concatenate all per-item markdown text into a single string.
4. `MarkdownPort.render(concatenated)` → HTML.
5. `_strip_directive_paragraphs(html)` (handles any nested lone `{% %}` directives).
6. `_render_nodes(html, augmented_context)` → children (a single `<ul>` with all `<li>`s).
7. Set as `_children`.

On collection change (iterable is `ReactiveList`/`ReactiveDict`): `_refresh()` repeats steps 1-7 and patches children.

**Reactive separation** (critical):
- **Field change** (e.g., `item.name` Signal changes): the per-field `TextElement(Signal)` handles updates fine-grained via `on_after_updating`. **No block re-render.**
- **Collection change** (add/remove/replace items): `on_after_updating` on the iterable triggers `_refresh()` → full block re-render (O(N)). **Block re-render occurs.**
- **`{% if %}` inside for** (e.g., `{% if item.active %}`): evaluated **statically per item** during steps 2-3. If `item.active` is a Signal and changes, the `{% if %}` does NOT re-evaluate (only collection change or `<p>`-content change triggers re-evaluation of the if). For reactive list-item conditionals, use the HTML-block escape hatch.

**Rationale**: This is the only architecture that delivers single `<ul>` + field-level reactivity. The O(N) collection re-render is acceptable for content pages (where collection changes are rare). The static-if limitation for merging loops is a documented trade-off with a well-defined escape hatch.

**Alternatives considered during planning**:

| Approach | Description | Outcome |
|---|---|---|
| A — Static pre-pass | Pre-expand `{% for %}` at text level without reactive wrapper; no collection reactivity | Rejected (snapshot-only) |
| B — Per-item DynamicElement | Each item as a standalone DynamicElement with its own reactive subtree | Rejected (no shared `<ul>`) |
| C — Post-hoc DOM merge | Render via `repeat()` then merge adjacent `<ul>` elements in DOM | Rejected (brittle DOM surgery) |
| D — Markdown dialect extension | Extend Markdown syntax to express loop-within-list natively | Rejected (non-standard) |
| **E — MarkdownForElement** | Reactive `DynamicElement` that concatenates per-item markdown text and renders via single `MarkdownPort` pass | **Selected** |
| F — Source-level rewrite | Rewrite `{% for %}` + `- ` lines to `<ul>{% for %}<li>` at source level; full incremental reactivity | Rejected (fragile, breaks on complex bodies) |

The MarkdownForElement approach is the sweet spot: correct merging for any body + field reactivity + collection reactivity (wholesale).

### D2: Expression-scoped loop-variable renaming

Loop variable renaming MUST be scoped to `{{ }}` and `{% %}` template expressions only. A naive global `\b{item}\b` replace would corrupt Markdown prose containing the loop variable name.

**Implementation**: For each item N, walk the body markdown text and identify `{{ }}` / `{% %}` spans. Within each span, replace occurrences of the loop variable name(s) with `__wmdf_{N}_{varname}`. For tuple unpacking (`{% for k, v in d %}`), both `k` and `v` are renamed per iteration (`__wmdf_N_k`, `__wmdf_N_v`).

**Rationale**: The renaming scope is limited to template expressions; prose remains intact. The `__wmdf_` prefix is reserved for framework-generated synthetic keys. The HOLE_PATTERN from Change 1 (`[a-zA-Z_]\w*(\.[a-zA-Z_]\w*)*`) validates the renamed paths.

### D3: Reserved prefix `__wmdf_`

All synthetic context keys generated by the for-expansion SHALL use the `__wmdf_` prefix (e.g., `__wmdf_0_item`, `__wmdf_1_item`). User-supplied context keys with this prefix MAY collide and cause unexpected behavior. The prefix SHALL be documented as a framework-reserved namespace.

**Rationale**: The prefix makes origin clear and reduces collision probability. A full collision-detection mechanism (UserWarning on collision) can be added in a follow-up.

### D4: Body-type detection — list vs non-list routing

`render_markdown`'s pipeline SHALL detect whether a `{% for %}` body, when rendered independently per item via `repeat()`, would produce list blocks that SHOULD be merged:

- **List body**: body lines (after stripping `{% if %}`/`{% endif %}` directives) start with `-`, `*`, `+`, or a digit followed by `.` or `)` (i.e., unordered/ordered list markers). Route to `MarkdownForElement`.
- **Non-list body**: headings (`#`), paragraphs (plain text), HTML blocks (lines starting with `<`), blockquotes (`>`), etc. Route to standard `repeat()` (unchanged from Change 6, fully reactive with reactive `{% if %}`).

**Rationale**: Lists have a natural merge expectation (multiple `- ` items → one `<ul>`). Headings, paragraphs, and other blocks do not — independent per-item rendering via `repeat()` produces the expected output. This heuristic maximizes reactivity (non-list for-loops stay on the fully-reactive `repeat()` path with reactive `{% if %}`) while fixing the list-use case.

### D5: Lifecycle — mirroring SwitchElement with shared `_run_refresh_sync`

`MarkdownForElement._render()` SHALL register `on_after_updating` callback nodes on the iterable (if reactive) during the initial render. The callback nodes SHALL be stored in `_callback_nodes` and destroyed on element cleanup (`_remove_element` → `consumer_destroy`).

`_refresh()` SHALL be `async def` and follow the `SwitchElement._refresh` pattern:
- Determine new children via re-expansion + re-render.
- Patch old children via `_patch_children`.
- Defer `on_after_rendering` lifecycle hooks via `start_defer_after_rendering` / `end_defer_after_rendering` when `_signal_activated` is True.

For sync invocation of the async `_refresh` from `on_after_updating` callbacks, `MarkdownForElement` SHALL use the shared `_run_refresh_sync(self._refresh, *args)` helper from `webcompy.elements.types._dynamic` (extracted in `refactor-element-foundations`), rather than duplicating the sync-wrapper logic.

### D6: Nested for and tuple unpacking

- **Nested `{% for %}`**: If a `MarkdownForElement` body contains another `{% for %}`, the inner for SHALL be recursively expanded during steps 2-3 (created as another `MarkdownForElement`, or routed to repeat() if non-list). Per-item renaming composite paths: `__wmdf_{outer}_{inner}_varname`.
- **Tuple unpacking**: `{% for k, v in dict %}` SHALL rename both loop variables to `__wmdf_N_k` and `__wmdf_N_v`, and inject both into context.
- **`{% if %}` inside `{% for %}`**: statically evaluated per item during step 2. The if condition is resolved against the per-item renamed context. Body content for truthy branches is emitted; falsy branches are omitted. This means `{% if %}` inside list-body `{% for %}` is NOT reactive to field changes (only re-evaluates on collection change).

**Rationale**: Nested for recursion follows the same merge logic. Tuple unpacking mirrors Change 2's `for`-binding design (D6). Static-if evaluation during expansion is the only way to achieve list merging — reactive if would require the `{% if %}` directive to appear at list-item line-start, which Markdown would not recognize as a list.

### D7: HTML-block escape hatch for fully-reactive list loops

For developers who need fully-reactive list loops (incremental O(1) patching + reactive `{% if %}`), the pattern `<ul>{% for item in items %}<li>{{ item }}</li>{% endfor %}</ul>` (HTML block) SHALL be documented. This uses `repeat()` + `switch()` from Changes 2-3 and is the preferred path for reactive collections in list contexts.

**Rationale**: HTML blocks pass through Markdown unchanged, so the template engine processes them with the HTML-first reactive pipeline. This escape hatch provides full reactivity for those who need it, without complicating the MarkdownForElement design.

## Risks / Trade-offs

- **[Risk] O(N) block re-render on collection change may be slow for large lists** → Mitigation: Content pages rarely have large frequently-changing lists. For large dynamic lists, use the HTML-block escape hatch (`<ul>{% for %}<li>...</li>{% endfor %}</ul>`). A future enhancement could add incremental (O(1)) patching for simple-list `MarkdownForElement`.
- **[Risk] `__wmdf_` prefix collision with user context keys** → Mitigation: The `__wmdf_` prefix is unlikely to be used by user code (double-underscore convention). Documented as reserved.
- **[Risk] List-body detection heuristic false positives/negatives** → Mitigation: The heuristic is conservative: list markers at line start after stripping if-directives. Edge cases (mixed list+other blocks) are rare. False negatives (list not detected) → falls back to repeat() (safe, just no merging). False positives (non-list routed to MarkdownForElement) → still produces correct output, just with re-render semantics instead of incremental.
- **[Trade-off] `{% if %}` inside merging for-loops is non-reactive to field changes** → Mitigation: Re-evaluates on collection change. HTML-block escape hatch for fully-reactive list-item conditionals. Documented prominently.
- **[Trade-off] Generates a new DynamicElement (~100 lines)** → Mitigation: follows established patterns (SwitchElement/RepeatElement). Minimal new surface area. Lives in `webcompy/template/` (not `elements/types/`) since it's Markdown-pipeline-specific.

## Open Questions

None — all design decisions resolved during planning phase.
