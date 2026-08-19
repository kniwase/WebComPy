# Design: fix-code-highlight-accuracy

## Context

See proposal.md — Why. All work is confined to the three built-in lexers under
`packages/webcompy/src/webcompy/ui/code_block/lexers/` plus their unit tests.
The lexers run in both environments (server-side for SSR/SSG and in-browser
under Pyodide), so they must remain pure-stdlib and produce deterministic
output: identical input must yield identical token streams on both sides,
otherwise hydration would see mismatched token spans.

Relevant current behavior (verified during exploration):

- `PythonLexer` defers the name after `class`/`def`/`async` into
  `pending_function_name` and only flushes it when an OP `(` arrives (or at
  end-of-stream). Parenthesis-less `class Foo:` never triggers a timely flush.
- `PythonLexer` emits all `OP` tokens as `TokenType.OPERATOR`; the existing
  `code-block` spec scenario for `def foo(): pass` expects `PUNCTUATION`.
- Python 3.12+ emits `FSTRING_START`/`FSTRING_MIDDLE`/`FSTRING_END` for
  f-strings; these fall through to the catch-all and become `IDENTIFIER`.
- `keyword.softkwlist` on 3.12 is `['_', 'case', 'match', 'type']`; the lexer
  checks soft keywords before builtins, so `type` is always `KEYWORD` despite
  being in `_BUILTINS`, and `_` is always `KEYWORD`.

## Goals / Non-Goals

**Goals:**

- Restore the round-trip invariant (`"".join(values) == source`) for all three
  built-in lexers; tokens are emitted strictly in source order.
- Fix every misclassification listed in the proposal with minimal, local
  changes and no new dependencies.
- Keep the change deterministic across server and browser runtimes.

**Non-Goals:**

- Grammar-perfect highlighting (e.g., full PEP 634 pattern grammar). A
  documented heuristic is acceptable where exact parsing is impractical.
- Standalone TOML times (`t = 10:20:30`) remain uncolored (pre-existing gap,
  not a regression).
- Changes to `highlight()`, `CodeBlock`, CSS, or the lexer registry — the
  rendering pipeline is untouched.

## Decisions

### D1: Emit the defined name immediately (class/def root fix)

In the NAME branch, when the pending def-like keyword is set, yield
`Token(TokenType.FUNCTION, value)` immediately and delete the entire
`pending_function_name` mechanism (variable, `(`-flush in the OP branch, and
end-of-stream flush).

- **Alternative considered (B)**: keep deferral but flush before every other
  yield. Produces identical visible output but keeps a stateful flush point at
  every emit site — more complexity for no benefit, and it still misorders
  relative to gap whitespace. Rejected.
- **Why immediate is safe**: in valid Python the NAME directly after
  `def`/`class`/`async def` is always the defined name. For `def foo ():` the
  FUNCTION span moves before the whitespace gap instead of after it — the
  concatenated text is identical, only span boundaries shift.

### D2: Classify `OP` as PUNCTUATION, merging only adjacent PUNCTUATION

Emit `Token(TokenType.PUNCTUATION, value)` from the OP branch, then wrap the
token generator in a small post-pass that merges *only* runs of consecutive
PUNCTUATION tokens (concatenating values). This makes the existing
`code-block` scenario (`def foo(): pass` → 1st `KEYWORD`, 3rd `FUNCTION`,
5th `PUNCTUATION ":"`) hold exactly: `( )` merges into one token.

- **Alternative**: merge all consecutive same-type tokens. Rejected — it would
  fuse `"\n"` + `"    "` IDENTIFIER runs and break the documented
  newline-preservation behavior and its tests.
- **Alternative**: keep OPERATOR and edit the `code-block` spec scenario
  instead. Rejected by user decision: the spec's token positions are the
  contract; the implementation aligns to it.
- Bundled theme maps `--tok-op` and `--tok-punct` to the same color in both
  the only shipped token set, so the visual output is unchanged.

### D3: f-strings via the 3.12 token types

Map `FSTRING_START`, `FSTRING_MIDDLE`, and `FSTRING_END` to `TokenType.STRING`,
resolving the constants with `getattr` and an empty-set fallback so the code
still runs if a runtime lacks them. Expression tokens inside `{...}` flow
through the normal classification path (NAME, OP, etc.), which is the desired
look. Format-spec middle text is also `FSTRING_MIDDLE` and inherits STRING —
acceptable approximation.

### D4: Contextual soft keywords via next-significant-token lookahead

Remove `type` and `_` from soft-keyword handling entirely (`type` then falls
through to `_BUILTINS` where it is already listed; `_` becomes IDENTIFIER).
For `match`/`case`, emit KEYWORD only when the *next significant token* in the
already-materialized token list (skipping NL/NEWLINE/INDENT/DEDENT/COMMENT) is
a NAME, STRING, or NUMBER; otherwise emit IDENTIFIER.

- **Rationale**: kills the common false positives (`match = ...`,
  `re.match(`, `x.case`) while keeping the common statement forms
  (`match command:`, `case 200:`, `case "ok":`, `case Foo():`).
- **Acknowledged approximation**: patterns starting with punctuation
  (`case [1, x]:`, `match (x, y):`) render the keyword as IDENTIFIER.
  Documented in the spec as acceptable.

### D5: Decorator `@` only at logical-line start

Track an `at_line_start` flag: true at start of input and after
NEWLINE/NL/INDENT tokens, false after any other significant token. Set
`pending_decorator` only when `@` is seen while `at_line_start` is true.
`a @ b` therefore never enters the decorator path; `@decorator` at line start
is unchanged.

### D6: TOML datetime restricted to RFC 3339 shapes

Replace the date pattern's greedy tail `(?:[Tt\s][^\n,}\]]*)?` with a strict
optional time part:
`\d{4}-\d{2}-\d{2}(?:[Tt ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:[Zz]|[+-]\d{2}:\d{2})?)?`
(TOML permits a space in place of `T`). Trailing comments and other line
content are tokenized normally again.

### D7: TOML integer formats and underscores

Extend the number pattern with
`0[xX][0-9A-Fa-f_]+ | 0[oO][0-7_]+ | 0[bB][01_]+` ahead of the decimal branch,
and make the decimal branch underscore-aware (`\d[\d_]*`) since TOML integers
commonly use `_` separators.

### D8: Bash special variables and comment position

- Variable pattern gains `\$\d+ | \$[@*#?$!-]` alongside the existing
  `$NAME`/`${NAME}` alternatives, still yielding a single IDENTIFIER token
  with the `$` preserved (per the existing requirement).
- Comment pattern becomes `(?:(?<=^)|(?<=[ \t]))\#[^\n]*` with the pattern
  compiled with `re.MULTILINE`, so `#` only starts a comment at line start or
  after horizontal whitespace. An unmatched mid-word `#` falls through to the
  gap path and round-trips as IDENTIFIER text.

## Risks / Trade-offs

- [Span classes for Python operators change from `tok-op o` to `tok-punct p`]
  → Mitigation: bundled theme colors both identically; the change is documented
  in the proposal's Impact for users with custom stylesheets.
- [Soft-keyword heuristic misclassifies punctuation-led patterns
  (`case [1, x]:`)] → Mitigation: documented as an accepted approximation in
  the spec; far less frequent than the false positives it eliminates.
- [Merge changes span granularity for operators] → Mitigation: visible text is
  identical; SSR and CSR use the same lexer so hydration trees match.
- [Pyodide/runtime lacking `FSTRING_*` constants] → Mitigation: `getattr`
  guards; behavior degrades to the current (uncolored) output instead of
  raising.

## Migration Plan

No migration. The fix is behavior-only inside the lexers; regenerating a site
(`webcompy generate`) picks up corrected output automatically. No API surface
changes.

## Open Questions

None.
