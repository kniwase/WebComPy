# Tasks: fix-code-highlight-accuracy

## 1. PythonLexer: class/def name emission and punctuation classification

- [ ] 1.1 Remove the `pending_function_name` machinery (variable, `(`-flush in the OP branch, end-of-stream flush) from `packages/webcompy/src/webcompy/ui/code_block/lexers/_python.py` and emit `Token(TokenType.FUNCTION, value)` immediately in the def-like NAME branch (design D1)
- [ ] 1.2 Emit `OP` tokens as `TokenType.PUNCTUATION` and add a post-pass that merges only consecutive PUNCTUATION tokens (design D2)
- [ ] 1.3 Add regression tests in `tests/test_code_block_lexers.py`: class name emitted in place (`class Counter:` + `def`), name not displaced by a later call (`class ChatMessage:` + call), name not appended at EOF (`class Event:`), class with bases (`class Foo(Bar):`), round-trip invariant across representative samples, and exact token positions for `def foo(): pass` (1st KEYWORD, 3rd FUNCTION, 5th PUNCTUATION `":"`)

## 2. PythonLexer: f-strings, soft keywords, decorator position

- [ ] 2.1 Map `FSTRING_START`/`FSTRING_MIDDLE`/`FSTRING_END` (resolved via `getattr` with empty-set fallback) to `TokenType.STRING` (design D3)
- [ ] 2.2 Implement contextual soft keywords: `type` and `_` removed from soft-keyword handling (`type` falls through to builtins); `match`/`case` emit KEYWORD only when the next significant token is NAME/STRING/NUMBER (design D4)
- [ ] 2.3 Restrict `pending_decorator` to logical-line start via an `at_line_start` flag (design D5)
- [ ] 2.4 Add regression tests for each delta-spec scenario: f-string literal coloring, `match = re.match(...)` vs `match command:`, `type(obj)` builtin, `for _ in ...` identifier, `a @ b` not a decorator, `@property` still a decorator

## 3. TomlLexer: strict datetime and integer formats

- [ ] 3.1 Replace the greedy date tail with the strict RFC 3339 time part in `packages/webcompy/src/webcompy/ui/code_block/lexers/_toml.py` (design D6)
- [ ] 3.2 Add hexadecimal/octal/binary integers and underscore-aware decimals to the number pattern (design D7)
- [ ] 3.3 Add regression tests: `d = 2024-01-01  # release date` splits date STRING and COMMENT, `2024-01-01T10:20:30Z` single STRING, `0x10`/`0o17`/`0b101` NUMBER, TOML round-trip samples

## 4. BashLexer: special variables and comment position

- [ ] 4.1 Extend the variable pattern with `\$\d+` and `\$[@*#?$!-]`, yielding a single IDENTIFIER with the `$` preserved, in `packages/webcompy/src/webcompy/ui/code_block/lexers/_bash.py` (design D8)
- [ ] 4.2 Restrict the comment pattern to line start or after horizontal whitespace with `re.MULTILINE` lookbehind (design D8)
- [ ] 4.3 Add regression tests: `echo $1` single IDENTIFIER `$1`, `echo a#b` no COMMENT with intact round-trip, `echo a # b` COMMENT `# b`, existing `$NAME`/`${NAME}` scenarios unchanged

## 5. Verification

- [ ] 5.1 Run `uv run python -m pytest tests/test_code_block_lexers.py tests/test_code_block_highlight.py --tb=short`, then the full `tests/` suite
- [ ] 5.2 Run `uv run ruff check .`, `uv run ruff format --check .`, and `uv run pyright`
- [ ] 5.3 Re-render `docs_app/documents/typed_realtime.md` through the in-memory SSR pipeline and confirm `ChatMessage`/`Event`/`Money`/`Payment` each appear as `tok-fn` spans at their definition sites with intact round-trip text
- [ ] 5.4 Run `uv run python -m webcompy generate` for `docs_app` and verify the regenerated `docs/documents/typed-realtime/index.html` code blocks (plus a spot check of one page each containing f-strings/TOML/Bash samples if present) via the inspect CLI
- [ ] 5.5 Run `python3 scripts/check-doc-spec-refs.py` to confirm doc/spec references stay valid
