# Tasks: feat-template-expression-language

## 1. Expression evaluator core

- [x] 1.1 Create `packages/webcompy/src/webcompy/template/_expression.py`: parse expressions via `ast.parse(mode="eval")`, validate against the node-type whitelist (BinOp/BoolOp/UnaryOp/Compare/IfExp/Subscript/Attribute/Call/List/Tuple/Dict/Set/Name/Constant), reject comprehensions/lambdas/walrus and `_`-prefixed attribute segments with `WebComPyException` (spec: expression-language requirement)
- [x] 1.2 Implement the evaluator in `_expression.py`: walk the AST resolving `Name` via `resolve_var`, unwrap `SignalBase` to `.value` on encounter, support operators/subscripts/attribute access/calls (Call func restricted to Name/Attribute)
- [x] 1.3 Implement the built-in filter registry (`upper/lower/title/capitalize/trim/length/join/default/replace/round/int/float/string/first/last/abs`) and `BitOr` reinterpretation: registered filter Name/Call on the right applies the filter (registry precedence), otherwise plain bitwise-or (spec: filter requirement)
- [x] 1.4 Replace `HOLE_PATTERN` regex extraction in `_holes.py` with a depth-aware scanner tracking `{`/`}` nesting and skipping braces inside string literals; keep strict-mode errors as expression parse/validation errors

## 2. Reactive integration smoke tests (risk burn-down, test-first)

- [x] 2.1 Add unit test pinning `repeat(Computed)` behavior: `repeat()` over a `Computed` wrapping a sliced `ReactiveList` reconciles on whole-value updates (design D3/D6, spec: `{% for %}` expression scenario)
- [x] 2.2 Add unit test pinning `SwitchElement` with a `Computed` case condition toggling when the underlying `Signal` crosses a threshold (spec: `{% if %}` expression scenario)

## 3. Text and attribute hole binding

- [x] 3.1 Extend `bind_text_part` in `_binder.py`: classify holes as plain-path (existing pass-through behavior unchanged) vs true expression (evaluate once, or wrap in `Computed` when any referenced value is `SignalBase`)
- [x] 3.2 Extend `resolve_attr` in `_binder.py` so attribute holes accept expressions, preserving existing Computed-wrapping and `format_value` semantics for mixed literal/expression attributes
- [x] 3.3 Unit tests for text/attribute expressions: static, reactive (Signal → re-render), filters, nested literals, error cases (tests/test_template_binder.py or new test_template_expressions.py)

## 4. Directive conditions and iterables

- [x] 4.1 Extend `bind_if` in `_binder.py`: parse `{% if %}`/`{% elif %}` conditions as expressions; Signal-referencing conditions become `Computed` case values for `SwitchElement`; plain paths keep current behavior
- [x] 4.2 Extend `bind_for` in `_binder.py`: parse iterable target as expression; Signal-referencing expressions wrap in `Computed` and route to `repeat()`; non-iterable resolution errors remain descriptive
- [x] 4.3 Unit tests for directive expressions (reactive threshold toggle, sliced iterable reconciliation, mixed Signal/static if-elif chain)

## 5. Comments and raw blocks

- [x] 5.1 Implement `{% raw %}...{% endraw %}` preprocessing in the compile path (`_cache.py`/`_parser.py` entry): protect raw content via `protect_lbrace` before parsing; raise `WebComPyException` on unclosed raw; verify binder-side `restore_protected` covers text and attribute outputs
- [x] 5.2 Implement `{# ... #}` comment stripping after raw protection (order: raw → comments), applied to both `render_template` and `render_markdown` paths
- [x] 5.3 Unit tests: comment stripping (incl. comment spanning template syntax), raw literal output (`{{ }}`, `{% %}`, `{# #}` inside raw), tags parsing inside raw, unclosed raw error, markdown code-block protection regression (spec: markdown protection requirement unchanged)

## 6. Specs, docs, and e2e

- [x] 6.1 Add SSR tests for expressions/comments/raw (tests/test_template_ssr.py)
- [x] 6.2 Add e2e page exercising expressions, filters, reactive conditions, and raw blocks in the browser (validates `ast` under Pyodide); register in e2e group config
- [x] 6.3 Update `docs_app/templates/document/limitations.py`: remove expression-language/comment/escaping limitations, document remaining subset limits (comprehensions/lambda/walrus/tests/`~`/custom filters), filter precedence, method-call mutation caveat, markdown raw-HTML `{# #}` stripping note, `{% raw %}` as the literal-`{{` mechanism
- [x] 6.4 Update `AGENTS.md` File→Spec Mapping row for `webcompy/template/_expression.py`; check `.opencode/skills/webcompy-review/SKILL.md` invariants for stale references to dot-path-only limitations and update if present

## 7. Verification

- [x] 7.1 Run `uv run ruff check . && uv run ruff format --check . && uv run pyright`
- [x] 7.2 Run `uv run python -m pytest tests/ --tb=short`
- [x] 7.3 Run `uv run python -m webcompy generate` (docs build) and the affected e2e group via `scripts/run-e2e-tests.sh`
- [x] 7.4 Run `openspec validate feat-template-expression-language`
