# Design: Loop Metadata and Unsupported-Directive Rejection

## Context

The template engine compiles `{% for %}` blocks through three binding paths in `packages/webcompy/src/webcompy/template/_binder.py`:

1. **Static** (`_bind_for_static`): plain `list`/`dict` iterables expanded eagerly via comprehension.
2. **ReactiveList** (`_bind_for_reactive`, single-arg): `repeat(signal, cb)` with no key → `RepeatElement._refresh()` performs a **full rebuild** of all children on every change.
3. **ReactiveDict** (`_bind_for_reactive`, two-arg): `repeat(signal, cb)` with dict keys → `RepeatElement._reconcile_children()` performs **key-based reconciliation**, reusing existing child DOM across add/remove/reorder.

Separately, markdown list-body for-loops go through `MarkdownForElement` (`_markdown_for.py`), which expands iterations **textually** (loop vars are renamed to `__wmdf_{n}_<var>` inside expressions, all iterations concatenated, then rendered once) and fully regenerates on refresh.

Directive scanning (`_scan_text_for_directives`, `_parser.py:112`) matches only `if|elif|else|endif|for|endfor` via `DIRECTIVE_PATTERN`. Any other `{% ... %}` span (e.g., `{% extends %}`, typo `{% endfo %}`) currently falls through as literal text and is rendered into output silently. `{% raw %}` blocks are protected before directive scanning, so raw content never reaches the scanner.

The `docs_app` limitations page duplicates (and drifts from) the spec's four "limitations shall be documented" requirements; the project direction is that the spec is the single source of truth.

## Goals / Non-Goals

**Goals:**

- `loop` metadata in all `{% for %}` bodies: `index` (1-based), `index0` (0-based), `revindex`, `revindex0`, `first`, `last`, `length` — always positionally correct, including across `ReactiveDict` reconciliation.
- Compile-time `WebComPyException` for known-unsupported Jinja2 directives and for unknown `{% word %}` spans, with concise messages.
- `template-engine` spec states the design intent (sugar layer, non-compatibility, composition-via-components) and is self-contained on limitations; `docs_app` limitations page removed.

**Non-Goals:**

- `{% else %}` on for, `break`/`continue`, `list[tuple]` unpacking, functional loop helpers (`loop.changed()` etc.).
- Jinja2 template inheritance/macros/includes — rejected as unsupported, never emulated.
- Changes to the public `repeat()` overload contract.
- A replacement docs page (spec-only consolidation).

## Decisions

### D1. `LoopMetadata` is a plain namespace object injected per iteration

A small internal class (no public export) holds the seven attributes. `_extend_for_ctx()` gains metadata construction and sets `new_ctx["loop"] = LoopMetadata(...)`. Because the expression evaluator unwraps `SignalBase` on attribute access and passes plain values through, `{{ loop.index }}` and `{% if loop.first %}` work transparently regardless of whether the attribute is a plain value or a `Computed`.

**Alternative considered:** injecting individual context keys (`__loop_index`, etc.) — rejected: pollutes the context namespace and breaks the natural `loop.index` dot-path syntax users expect from Jinja2.

### D2. Static and ReactiveList loops use plain metadata values

Static loops compute values from `enumerate(items)` directly. ReactiveList loops also use plain values: the unkeyed `_refresh()` path fully rebuilds all children on every change, so generation-time values are always fresh. No `RepeatElement` changes are needed for lists.

**Alternative considered:** uniform `Computed`-backed metadata everywhere — rejected as unnecessary complexity; rebuild semantics already guarantee exactness, and uniformity is an implementation detail invisible to users (the observable contract "metadata is always correct" holds either way).

### D3. ReactiveDict loops derive metadata from the source signal, not from `RepeatElement`

DOM order after reconciliation equals dict insertion order (`_iter_items()` iterates `self._sequence.value.items()`). Therefore position can be derived from the `ReactiveDict` signal itself, with **zero changes to `RepeatElement`**:

- One shared per-loop `positions = Computed(lambda: {k: i for i, k in enumerate(signal.value)})` — O(n) per recompute, shared by all items (avoids O(n²) `list.index` scans).
- Per-item attributes are `Computed`s over `positions`: `index = Computed(lambda: positions.value[k] + 1)`, `index0`, `revindex`/`revindex0` (= `length - index0` / `length - index`), `first` (= `index0 == 0`), `last` (= `index == length`), and one shared `length = Computed(lambda: len(positions.value))`.
- One-variable dict loops (`{% for v in d %}`) internally use the two-arg dict `repeat()` overload so the callback receives the key `k` needed for position lookup; observable behavior is unchanged (dict overloads route identically).
- Removed keys: their children are destroyed during reconciliation; downstream subscribers (TextElement etc.) unsubscribe from the metadata `Computed`s, which then become unobserved and release their dependency on `positions` via graph cleanup. No leak.

**Alternative considered:** `RepeatElement` owns a keys-order `Signal` and pushes position updates to children — rejected: touches the reconciled-element core (recently stabilized by #218–#221), duplicates state already derivable from the source signal, and risks divergence between signal order and DOM order.

### D4. `MarkdownForElement` gets plain metadata via the existing textual-renaming mechanism

`augmented_ctx[f"__wmdf_{n}_loop"] = LoopMetadata(...)` with plain values, and `loop` is renamed in expressions exactly like declared loop vars. Full-regeneration semantics make plain values exact on every refresh. Renaming happens only inside expressions (`_rename_in_expressions`), so literal text "loop" is unaffected.

### D5. Three-way directive classification at compile time

`_parser.py` gains `_GENERIC_DIRECTIVE_RE = r"\{%\s*(?P<name>[a-zA-Z_][a-zA-Z0-9_]*)\b[^%]*%\}"`. `_scan_text_for_directives` iterates it and dispatches:

- name ∈ supported (`if|elif|else|endif|for|endfor`) → existing token creation.
- name ∈ `_KNOWN_UNSUPPORTED_DIRECTIVES` (Jinja2 tag set minus supported: `extends`, `block`/`endblock`, `macro`/`endmacro`, `call`/`endcall`, `include`, `import`, `from`, `set`, `with`/`endwith`, `filter`/`endfilter`, `do`, `trans`/`endtrans`, `pluralize`, `autoescape`/`endautoescape`, `debug`) → `WebComPyException("{% <name> %} is not supported in WebComPy templates")`.
- otherwise → `WebComPyException("Unknown template directive: {% <name> %}")`.

Classification happens at compile time (inside the `get_or_compile` path), so errors surface before any DOM work and are shared by `render_template` and the markdown text path. Markdown for-block splitting (`_markdown_for.py`) continues to match only supported directives for block detection; unsupported directives in markdown flow into the compiled HTML path and are rejected there. Directive scanning only inspects text nodes — `{%` inside attribute values stays literal (documented).

### D6. `loop` shadowing follows Jinja2 innermost-wins semantics

Nested loops: the inner `_extend_for_ctx` assignment shadows the outer `loop`. A user loop variable literally named `loop` shadows the metadata for that body (loop vars are assigned after metadata in `_extend_for_ctx`). Both behaviors are spec'd, not left implicit.

### D7. Spec becomes the single source of truth for design intent and limitations

- Purpose section expanded: template engine = sugar over Element/Component system; Jinja2-inspired, not compatible; composition via components/slots; inheritance (`extends`/`block`/`macro`/`include`) permanently rejected by design.
- The four limitation requirements are reworded self-contained (drop "the framework documentation SHALL…" phrasing).
- The for-loop limitation requirement is modified: loop metadata removed from the NOT-supported list; `{% else %}` on for, `break`/`continue`, `list[tuple]` unpacking remain documented.
- `docs_app` limitations page + route deleted; AGENTS.md and review-skill references updated if present.

## Risks / Trade-offs

- [Breaking: templates with stray `{% %}` spans now raise at compile time] → `{% raw %}` is the documented escape hatch; only invalid/typo'd templates are affected; messages name the offending directive.
- [Position Computeds add reactive-graph nodes per dict-loop item] → one shared `positions` Computed per loop bounds recompute cost to O(n); attribute Computeds are lazy and unobserved ones are graph-cleaned.
- [`ReactiveDict` without positional mutations (e.g., single value update) still re-evaluates all position Computeds] → Computed equality check (`old is new or old == new`) suppresses downstream notification when positions are unchanged.
- [`loop` collides with an existing context variable] → intentional Jinja2-consistent shadowing, documented in spec with a scenario.
- [Directive names are matched case-sensitively; `{% Extends %}` would be "unknown" rather than "unsupported"] → acceptable: both messages are concise errors; Jinja2 tags are lowercase by convention.

## Migration Plan

No code migration needed. Template authors hitting the new compile-time errors either fix the directive or wrap literal `{%` output in `{% raw %}`. The removed `docs_app` page URL (`/documents/limitations`) falls back to the router's Not Found handling; no redirect is provided (docs site is pre-release).

## Open Questions

None.
