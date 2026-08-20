# Proposal: fix-code-highlight-accuracy

## Why

The built-in syntax-highlighting lexers produce incorrect output for several
common constructs. Most visibly, class names in parenthesis-less Python class
definitions (`class Foo:`) disappear from the rendered output or reappear glued
onto unrelated call sites — confirmed on the published docs site
(`docs/documents/typed-realtime/index.html` SSG output), where
`class ChatMessage:` renders as `class :` while `ChatMessage` is emitted in
function-name purple immediately before the `(` of `use_websocket(...)`, and
`Money` is lost entirely. Beyond that, f-strings render completely uncolored on
Python 3.12+, TOML dates swallow trailing comments into the string token, and
soft keywords (`match`, `case`, `type`, `_`) are always keyword-colored even in
ordinary expression positions such as `match = re.match(...)` or
`for _ in range(...)`. The Python lexer has also drifted from the existing
`code-block` spec scenario, which requires operator tokens to be classified as
`PUNCTUATION`.

## What Changes

- **PythonLexer — class/def name emission (root fix)**: emit the name following
  `class`/`def`/`async def` immediately as a `FUNCTION` token at its source
  position. Remove the deferred `pending_function_name` machinery that only
  flushed on a later `(` operator (or at end-of-stream), which caused the name
  to be lost, mispositioned, or appended at the end of the block.
- **PythonLexer — operator classification**: classify Python `OP` tokens per
  Pygments conventions: `(`, `)`, `[`, `]`, `{`, `}`, `:`, `,`, `;` as
  `PUNCTUATION`, all other operators as `OPERATOR`. This satisfies the
  `code-block` spec scenario's intent (`:` and brackets are `PUNCTUATION`)
  while matching Pygments stylesheet semantics. Emitted span classes change
  from `tok-op o` to `tok-punct p` for those nine characters; both map to the
  same color in the bundled theme, so the bundled visual output is unchanged.
- **PythonLexer — f-strings**: yield `FSTRING_START`, `FSTRING_MIDDLE`, and
  `FSTRING_END` tokens (Python 3.12+) as `STRING` so f-string literal content
  is colored like other strings.
- **PythonLexer — soft keywords in context**: treat `match`/`case` as
  `KEYWORD` only when the next significant token can start a pattern
  (NAME/STRING/NUMBER); treat `type` as `BUILTIN` and `_` as `IDENTIFIER`
  instead of keywords.
- **PythonLexer — decorator vs matmul**: only treat `@` as starting a decorator
  when it appears at statement start (beginning of input or immediately after a
  newline/indent), so `a @ b` no longer marks `b` as a decorator.
- **TomlLexer — datetime pattern**: restrict the date/time pattern to
  RFC 3339 shapes so `d = 2024-01-01  # comment` no longer swallows the
  trailing comment (and any other line content) into the `STRING` token.
- **TomlLexer — integer formats**: recognize hexadecimal (`0x`), octal (`0o`),
  and binary (`0b`) integers as `NUMBER`.
- **BashLexer — special variables**: recognize `$1`, `$@`, `$$`, `$?`, `$!`,
  `$*`, `$#` as single `IDENTIFIER` tokens instead of splitting them.
- **BashLexer — comment start**: treat `#` as starting a comment only at line
  start or after whitespace, so `echo a#b` no longer truncates the word.
- **New invariant**: the concatenation of all emitted token values SHALL equal
  the input source for every built-in lexer (round-trip guarantee).

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `syntax-highlight-lexers`: strengthen the source-order requirement into a
  round-trip invariant; add requirements for immediate class/def name emission,
  f-string token classification, contextual soft keywords, decorator-at-line-start,
  Python `OP` → `PUNCTUATION` classification per the Pygments split, TOML strict
  datetime and extended integer formats, Bash special variables, and Bash
  comment-start positioning.
- `code-block`: correct the "Python code is tokenized with tokenize" scenario,
  which asserted a token position (`fifth token SHALL be PUNCTUATION ":"`) that
  no implementation ever satisfied; the scenario now asserts the Pygments-true
  classification of `(`, `)`, and `:` as `PUNCTUATION`.

## Known Issues Addressed

- Docs site `typed-realtime` page renders broken Python samples (verified in
  the generated SSG HTML): `class ChatMessage:` → `class :` with `ChatMessage`
  glued to `use_websocket(`; `class Event:` → `class :` with `Event` glued to
  `use_websocketEvent(`; `class Money:` name lost entirely (overwritten by the
  following `def encode_money`); `class Payment:` name glued to
  `app.di_scopePayment():`.

## Non-goals

- Adopting Pygments or adding new lexers/languages.
- Dark-theme token color design or any CSS color changes.
- Changes to `docs_app` content — the Markdown sources are correct; the
  renderer was wrong.
- Cleanup of the unreachable `[`/`]` entries in `BashLexer._KEYWORDS` (no
  behavior change; hygiene only).
- Perfect grammar-accurate classification (e.g., full pattern-matching grammar
  for `match`/`case`); a documented approximation is acceptable for
  highlighting.

## Impact

- **Code**: `packages/webcompy/src/webcompy/ui/code_block/lexers/_python.py`,
  `packages/webcompy/src/webcompy/ui/code_block/lexers/_toml.py`,
  `packages/webcompy/src/webcompy/ui/code_block/lexers/_bash.py`
- **Tests**: `tests/test_code_block_lexers.py`, `tests/test_code_block_highlight.py`
- **Specs**: `openspec/specs/syntax-highlight-lexers/spec.md` (delta)
- **Output compatibility**: Python operator spans change class from
  `tok-op o` to `tok-punct p`. The bundled theme maps both to the same color,
  so bundled rendering is visually unchanged; custom user stylesheets that
  target `.tok-op` for Python code would need to target `.tok-punct` instead.
