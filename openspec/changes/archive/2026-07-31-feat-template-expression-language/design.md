# Design: feat-template-expression-language

## Context

The template engine (`packages/webcompy/src/webcompy/template/`) compiles template source via stdlib `html.parser.HTMLParser` into an AST (`_ast.py`), caches it (`_cache.py`), and binds it to a context (`_binder.py`). `{{ }}` holes are extracted by `HOLE_PATTERN` (`_holes.py:10`), a regex restricted to dotted variable paths; `split_text(..., strict=True)` actively raises on any other `{{ ... }}` content. `{% if %}` conditions and `{% for %}` iterable targets are likewise validated as dotted paths (`_binder.py:48-52`).

Reactivity today follows an implicit-Computed pattern: `resolve_attr` (`_binder.py:101-124`) wraps attribute interpolation in `Computed` when any hole resolves to a `SignalBase`; text holes pass `SignalBase` values straight to `TextElement`; `{% if %}` passes Signal conditions to `SwitchElement` cases; `{% for %}` passes Signal iterables to `repeat()`. The signal graph uses dynamic dependency tracking (`_active_consumer` ContextVar), so any `.value` read inside a `Computed` evaluation registers a dependency automatically.

Static verification (no spike required) confirmed all consumers accept `Computed` without changes:

- `TextElement` and `RawHTMLElement` accept any `SignalBase` (`_text.py:44-48`)
- `Element` attributes accept any `SignalBase` (`_element.py:59-60`)
- `SwitchElement` case values may be `SignalBase` and are subscribed via `on_after_updating` (`_switch.py:46,73-75`)
- `RepeatElement` requires only `isinstance(sequence, SignalBase)` plus `.value`/`on_after_updating` (`_repeat.py:70-77,147`)

## Goals / Non-Goals

**Goals:**

- A safe subset of Python expressions in `{{ }}` holes, `{% if %}`/`{% elif %}` conditions, and `{% for %}` iterable targets
- Jinja2-style filters via `|` with a built-in filter registry
- Reactive re-evaluation: expressions referencing Signals behave like implicit `Computed`
- `{# ... #}` comments and `{% raw %}...{% endraw %}` literal blocks
- Full backward compatibility for existing templates

**Non-Goals:**

- Comprehensions, lambdas, walrus/assignment expressions
- Jinja2 tests (`is defined`), `~` operator, custom filter registration API
- Expressions in `@event`, `:ref`, `:prop`
- SVG namespace support; full Jinja2 compatibility

## Decisions

### D1: Grammar = Python `ast` subset with whitelist validation (not a Jinja2 dependency)

Expressions are parsed with `ast.parse(source, mode="eval")` at template compile time and validated against a whitelist of node types: `BinOp` (arith/bitwise), `BoolOp`, `UnaryOp`, `Compare` (incl. `in`/`is`), `IfExp`, `Subscript`, `Attribute`, `Call`, `List`/`Tuple`/`Dict`/`Set` literals, `Name`, `Constant`. Calls are restricted: the function must be a `Name` or `Attribute`, and no attribute segment may start with `_` (blocks dunder/private access).

*Alternatives considered*: (a) Depend on Jinja2 at runtime — rejected: adds a heavy browser-side dependency and Jinja2's semantics (one-time evaluation) conflict with WebComPy reactivity; (b) Hand-written expression parser — rejected: `ast` is pure-Python stdlib, available under Pyodide, and Python expressions are the natural fit for a Python framework.

### D2: `|` is reinterpreted as filter application when the right side names a registered filter

`{{ name | upper }}` parses as `BinOp(BitOr)`. At validation time, if the right operand is a `Name` matching the filter registry, or a `Call` whose func is such a `Name` (extra args become filter arguments), the node is reinterpreted as a filter application. Otherwise it evaluates as a plain bitwise-or. Chains (`a | b | c`) work naturally via left-associativity. Filter registry names take precedence over context variables on the right of `|` (documented).

*Alternatives considered*: (a) Always bitwise-or — rejected: filters are a core Jinja2 idiom the change aims to support; (b) Always filter — rejected: would silently break legitimate integer bitwise-or expressions.

### D3: Signal-containing expressions are wrapped in `Computed`; plain paths keep the pass-through fast path

At bind time, each hole is classified:

- **Plain path** (only `Name`/`Attribute` chain, i.e. the old grammar): resolve via `resolve_var` and behave exactly as today — a resolved Signal is passed through unwrapped to `TextElement`/attribute handling, preserving fine-grained binding and existing semantics.
- **True expression** (anything else): resolve referenced variables; if any resolved value is a `SignalBase`, wrap evaluation in `Computed(eval_closure)`; otherwise evaluate once (Jinja2-like one-time semantics). Inside evaluation, encountering a `SignalBase` reads `.value` (unwrap), which both yields the operand and registers the dependency. Unwrapping a `ReactiveList`/`ReactiveDict` yields the raw collection — a coarse dependency, consistent with the known issue that these collections notify on any mutation.

The same classification applies to `{% if %}`/`{% elif %}` conditions (Computed → `SwitchElement` case value) and `{% for %}` iterable targets (Computed → `repeat()`), reusing existing reactive paths with zero changes to element classes.

*Alternatives considered*: (a) Route plain paths through the evaluator too — rejected: changes existing fine-grained semantics and adds overhead for no benefit; (b) One-time evaluation for all expressions (true Jinja2) — rejected: `{{ count }}` updating while `{{ count + 1 }}` does not would be a confusing, inconsistent mental model.

### D4: Hole extraction uses a depth-aware scanner, not a regex

`HOLE_PATTERN`'s non-greedy `(.*?)` terminates early on nested literals such as `{{ {'a': {'b': 2}} }}`. Hole extraction becomes a scanner that tracks `{`/`}` depth and skips braces inside string literals, so any expression the grammar accepts is extracted correctly. The strict-mode error for unparsable `{{ ... }}` content is preserved, now reported as an expression parse/validation error.

### D5: Raw and comment handling are source-level preprocessing, ordered raw-first

Before `HTMLParser.feed()` (inside the compile path, so both `render_template` and `render_markdown` benefit):

1. `{% raw %}...{% endraw %}` spans are located and every `{` inside them is replaced with the existing `PROTECTED_LBRACE_PLACEHOLDER` mechanism (`protect_lbrace`), making their `{{`, `{#`, and `{%` invisible to all later stages. Tags inside raw still parse as elements (Jinja2-consistent); binder-side `restore_protected` already covers text and attribute output paths. Unclosed `{% raw %}` raises a template error.
2. `{# ... #}` comments are stripped. Raw-protected content contains no literal `{#`, so comments inside raw survive correctly.

*Alternatives considered*: (a) Parser-state flags (raw depth counter in `TemplateTreeBuilder`) — rejected: preprocessing reuses the proven placeholder mechanism and keeps the parser untouched; (b) Documenting `<!-- -->` as the only comment syntax — rejected: `{# #}` fits the Jinja2 lineage and works in attribute-free positions where HTML comments are awkward.

### D6: No changes to `@event`, `:ref`, `:prop`

`@event` handlers must remain callable references resolved by dotted path (with existing modifier rejection); `:ref` must remain a `DomNodeRef`; `:prop` keeps path resolution. These are identity/reference bindings, not value expressions.

## Risks / Trade-offs

- [Markdown raw-HTML passthrough contains `{# ... #}` gets stripped] → GFM raw HTML blocks pass through verbatim into the same compile path; stripping applies to them too. This matches Jinja2 behavior and is documented on the limitations page. Markdown code blocks/spans are unaffected because `protect_lbrace` already replaces all `{` before this stage (`_markdown_blocks.py:1156`, `_markdown_inline.py:981`).
- [`ast` under Pyodide misbehaves] → `ast` is pure-Python stdlib bundled with Pyodide; an e2e page exercising expressions in the browser validates this during implementation (task-level test, no spike needed).
- [`repeat(Computed)` reconciliation semantics differ from `ReactiveList`] → Interface compatibility is verified statically (`_repeat.py:70-77`); a dedicated test in the first implementation task pins whole-value-update reconciliation behavior.
- [Method calls can mutate state from templates (e.g. `{{ items.append(1) }}`)] → Same exposure as Jinja2; templates are developer-authored. Documented; the whitelist still blocks dunder/private access.
- [Filter name shadows context variable on right of `|`] → Registry precedence is deterministic and documented (D2).
- [Evaluation errors surface at render time, not compile time] → Same as today for missing variables; expression *syntax* errors are caught at compile time via `ast.parse`.

## Migration Plan

No migration needed. All existing templates are valid under the new grammar (dotted paths are a subset) and keep identical binding behavior via the plain-path fast path (D3). Rollback is reverting the change; no persistent state or generated artifacts are affected.

## Open Questions

None. All scoping decisions (grammar extent, filter semantics, application points, preprocessing order) were resolved during exploration and recorded in D1–D6.
