# Proposal: feat-template-expression-language

## Why

The WebComPy template engine currently restricts `{{ }}` interpolation to dotted variable paths only, and this restriction is documented as an intentional limitation. In practice this forces every derived value (arithmetic, comparisons, slicing, string formatting) out of the template and into explicitly named `Computed` objects, which adds boilerplate for trivial derivations. Additionally, templates have no comment syntax and no way to emit literal `{{ }}`, both of which are standard in the Jinja2 lineage the template syntax follows. Extending the expression language in a Jinja2-like direction — while keeping WebComPy's reactive semantics — removes this friction without abandoning the deliberate "no arbitrary code in templates" design.

## What Changes

- `{{ }}` holes accept a safe subset of Python expressions (operators, comparisons, boolean logic, subscripts, attribute access, method calls, ternary expressions, list/tuple/dict literals) instead of only dotted paths.
- Jinja2-style filters are supported via `|` reinterpretation (e.g., `{{ name | upper }}`, `{{ items | join(', ') }}`) backed by a built-in filter registry.
- Expressions containing `Signal` references are automatically wrapped in `Computed` so they re-evaluate reactively (extending the existing implicit-Computed pattern already used for attribute interpolation).
- `{% if %}` / `{% elif %}` conditions and `{% for %}` iterable targets accept expressions, not just dotted paths.
- `{# ... #}` template comments are stripped at compile time.
- `{% raw %}...{% endraw %}` blocks emit their content literally (no hole/directive processing).
- The documented limitations page is updated: the expression-language, comment, and escaping limitations are removed; the markdown raw-HTML `{# #}` passthrough edge case is documented.

Backward compatibility is preserved: dotted paths are a valid subset of the new expression grammar, and plain-path holes keep their existing fine-grained pass-through behavior (Signals are passed through unwrapped, exactly as today).

## Capabilities

### New Capabilities

### Modified Capabilities

- `template-engine`: `{{ }}` interpolation, `{% if %}`/`{% elif %}` conditions, and `{% for %}` iterable targets gain expression support with reactive re-evaluation; template comments (`{# #}`) and raw blocks (`{% raw %}`) are added to the syntax.

## Known Issues Addressed

None. This change does not resolve any known issue from the project context; it removes documented intentional limitations of the template engine.

## Non-goals

- Comprehensions, generator expressions, lambda, assignment/walrus expressions in templates.
- Jinja2 tests (`is defined`, `is none`, etc.) and the `~` concatenation operator.
- A user-facing API for registering custom filters (the registry is internal for v1).
- Expressions in `@event` attributes (handlers must remain callable references resolved by path).
- Changes to `:ref` / `:prop` attribute semantics.
- SVG namespace support (`createElementNS`, case-preserving attribute parsing) — tracked separately; `raw_html()` remains the documented workaround.
- Full Jinja2 compatibility (autoescaping, template inheritance, includes, macros).

## Impact

- **Code**: `packages/webcompy/src/webcompy/template/` — new `_expression.py` (parser/validator/evaluator/filter registry); `_holes.py` (depth-aware hole scanner replacing the regex); `_parser.py` (raw/comment preprocessing); `_binder.py` (expression binding with Computed wrapping for text, attributes, `{% if %}`, `{% for %}`).
- **Specs**: `openspec/specs/template-engine/spec.md` (delta).
- **Docs**: `docs_app/templates/document/limitations.py` (remove lifted limitations, document markdown raw-HTML `{# #}` note).
- **Tests**: `tests/test_template_*.py` (unit, reactive re-evaluation, SSR); one e2e page exercising expressions in the browser (also validates `ast` availability under Pyodide).
- **APIs**: No breaking changes. Existing templates behave identically.
