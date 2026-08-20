# syntax-highlight-lexers Specification

## Purpose
TBD - created by archiving change feat-ui-toolkit-foundation. Update Purpose after archive.
## Requirements
### Requirement: The framework SHALL auto-register built-in lexers on `webcompy.ui.code_block` import

When `webcompy.ui.code_block` is imported, the framework SHALL call `register_lexer(PythonLexer(), source="builtin")`, `register_lexer(BashLexer(), source="builtin")`, and `register_lexer(TomlLexer(), source="builtin")` exactly once.

#### Scenario: Importing registers built-ins

- **WHEN** a developer writes `from webcompy.ui.code_block import CodeBlock`
- **THEN** the `python`, `bash`, and `toml` lexers SHALL be available via `get_lexer("python")` (and aliases / file extensions)
- **AND** `list_lexers()` SHALL include at least these three entries with `source == "builtin"`

#### Scenario: Re-importing does not double-register

- **WHEN** `webcompy.ui.code_block` is imported twice in the same process
- **THEN** each built-in lexer SHALL appear exactly once in the registry

### Requirement: The framework SHALL provide a `LexerNotFoundError` exception

The framework SHALL provide a `webcompy.ui.code_block.LexerNotFoundError` exception class that subclasses `KeyError` and is raised by `get_lexer` when no lexer matches the requested name, alias, or file extension.

#### Scenario: Error includes available lexers

- **WHEN** `get_lexer("nonexistent")` is called
- **THEN** `LexerNotFoundError` SHALL be raised
- **AND** the error message SHALL list the currently registered primary names

### Requirement: The framework SHALL provide a `LexerInfo` dataclass for introspection

The framework SHALL provide a `webcompy.ui.code_block.LexerInfo` frozen dataclass with fields `name: str`, `aliases: tuple[str, ...]`, `file_extensions: tuple[str, ...]`, and `source: str`. The `source` field is one of `"builtin"`, `"pygments:<lexname>"`, or `"custom"`.

#### Scenario: Inspecting a built-in lexer

- **WHEN** `list_lexers()` is called after importing `webcompy.ui.code_block`
- **THEN** each entry for a built-in SHALL have `source == "builtin"`
- **AND** the entry SHALL include the lexer's `name`, `aliases`, and `file_extensions`

### Requirement: The framework SHALL define a `register_lexer` API that supports override and source labeling

`register_lexer(lexer, *, override: bool = False, source: str = "custom")` SHALL register a lexer. If a lexer with the same `name` already exists, the function SHALL raise `ValueError` unless `override=True`. The `source` parameter SHALL be stored on the lexer for later introspection via `list_lexers`.

#### Scenario: Forcing override of a built-in

- **WHEN** a developer calls `register_lexer(MyBetterPythonLexer(), override=True)`
- **THEN** the existing `python` lexer SHALL be replaced
- **AND** subsequent `get_lexer("python")` calls SHALL return the new instance
- **AND** `list_lexers()` SHALL show the new lexer with `source == "custom"` (the value passed)

### Requirement: Lexers SHALL yield tokens in source order

`Lexer.tokenize(code)` SHALL yield `Token` objects in the order they appear in the source code. The combined `value` of consecutive tokens of the same `type` MAY be merged by the implementation, but the visible output SHALL be identical to a sequence of distinct tokens. For every built-in lexer, the concatenation of all emitted token values SHALL equal the input source exactly (round-trip invariant): tokenization MAY reclassify or merge spans but SHALL NOT drop, duplicate, or reorder source text.

#### Scenario: Token order matches source order

- **WHEN** `PythonLexer().tokenize("a + b")` is called
- **THEN** the iterator SHALL yield `a`, `+`, `b` (and any whitespace tokens) in that order
- **AND** no token SHALL be yielded out of order

#### Scenario: Round-trip preserves the source text

- **WHEN** any built-in lexer's `tokenize` is called with arbitrary source code
- **THEN** `"".join(token.value for token in tokens)` SHALL equal the input string

#### Scenario: Class definition keeps the class name in place

- **WHEN** `PythonLexer().tokenize` is called with `"class Counter:\n    def __init__(self):\n        self.count = 0\n"`
- **THEN** a `Token(TokenType.FUNCTION, "Counter")` SHALL be emitted between the `class` keyword and the `:` punctuation
- **AND** the concatenation of all token values SHALL equal the input

### Requirement: Lexers SHALL handle empty input and invalid input gracefully

`Lexer.tokenize("")` SHALL yield no tokens. `Lexer.tokenize` for syntactically invalid input (e.g., unclosed strings) SHALL yield as many tokens as it can determine and SHALL NOT raise an exception.

#### Scenario: Empty input yields no tokens

- **WHEN** any built-in lexer's `tokenize` is called with `""`
- **THEN** the iterator SHALL yield zero tokens

#### Scenario: Invalid Python still tokenizes

- **WHEN** `PythonLexer().tokenize("def foo(:")` is called (syntax error)
- **THEN** the iterator SHALL yield tokens for the parts that can be parsed
- **AND** no exception SHALL be raised

### Requirement: BashLexer SHALL yield variable references as IDENTIFIER tokens

`BashLexer().tokenize` SHALL recognize shell variable references of the form `$NAME` and `${NAME}` (where `NAME` matches `[A-Za-z_][A-Za-z0-9_]*`). For each reference, the lexer SHALL yield a single `Token(TokenType.IDENTIFIER, value)` token whose `value` preserves the reference exactly as written — the leading `$` and, for the braced form, the surrounding braces SHALL be kept in the `value`.

#### Scenario: Bare variable reference

- **WHEN** `BashLexer().tokenize("echo $HOME")` is called
- **THEN** the iterator SHALL yield a `Token(TokenType.IDENTIFIER, "$HOME")`
- **AND** it SHALL NOT yield any token whose `value` is `"HOME"`

#### Scenario: Braced variable reference

- **WHEN** `BashLexer().tokenize("echo ${PATH}")` is called
- **THEN** the iterator SHALL yield a `Token(TokenType.IDENTIFIER, "${PATH}")`
- **AND** it SHALL NOT yield any token whose `value` is `"PATH"`

### Requirement: PythonLexer SHALL emit the defined name immediately after `class`/`def`

When `PythonLexer` encounters a NAME token following the `def`, `class`, or `async def` keywords, it SHALL emit that name as a `Token(TokenType.FUNCTION, name)` at its source position, without waiting for any subsequent token. This SHALL hold whether or not the definition is followed by parentheses.

#### Scenario: Function name follows def

- **WHEN** `PythonLexer().tokenize("def foo(): pass")` is called
- **THEN** a `Token(TokenType.FUNCTION, "foo")` SHALL be emitted immediately after the whitespace token following the `def` keyword

#### Scenario: Class name without parentheses is emitted in place

- **WHEN** `PythonLexer().tokenize` is called with `"class Event:\n    type: str\n"`
- **THEN** a `Token(TokenType.FUNCTION, "Event")` SHALL be emitted before the `:` token
- **AND** no token SHALL be emitted after the final newline

#### Scenario: Class name is not displaced by a later call

- **WHEN** `PythonLexer().tokenize` is called with `"class ChatMessage:\n    user: str\n\nws = use_websocket(\"/api/chat\")\n"`
- **THEN** the `Token(TokenType.FUNCTION, "ChatMessage")` SHALL appear before the `:` token of the class line
- **AND** no token with value `"ChatMessage"` SHALL be emitted adjacent to the `use_websocket` call's `(` operator

#### Scenario: Class with bases still highlights the name

- **WHEN** `PythonLexer().tokenize("class Foo(Bar):\n    pass\n")` is called
- **THEN** a `Token(TokenType.FUNCTION, "Foo")` SHALL be emitted before the `(` token
- **AND** `Bar` SHALL be emitted as `TokenType.IDENTIFIER`

#### Scenario: Defined name shadows a builtin

- **WHEN** `PythonLexer().tokenize("def type(x):\n    return x\n")` is called
- **THEN** `type` SHALL be emitted as `TokenType.FUNCTION`

### Requirement: PythonLexer SHALL classify operator tokens per Pygments conventions

`PythonLexer` SHALL emit Python `OP` tokens whose value is one of `(`, `)`, `[`, `]`, `{`, `}`, `:`, `,`, `;` as `TokenType.PUNCTUATION`, and all other `OP` tokens as `TokenType.OPERATOR`. This mirrors the Pygments `Punctuation`/`Operator` split so Pygments stylesheets color the token spans correctly.

#### Scenario: Punctuation characters in a def statement

- **WHEN** `PythonLexer().tokenize("def foo(): pass")` is called
- **THEN** the first token SHALL be `Token(TokenType.KEYWORD, "def")`
- **AND** the third token SHALL be `Token(TokenType.FUNCTION, "foo")`
- **AND** the tokens for `(`, `)`, and `:` SHALL be `TokenType.PUNCTUATION`

#### Scenario: Operators are not punctuation

- **WHEN** `PythonLexer().tokenize("x = a[0] + f(b, c)")` is called
- **THEN** the tokens for `=`, `+`, and `.` SHALL be `TokenType.OPERATOR`
- **AND** the tokens for `[`, `]`, `(`, `,`, and `)` SHALL be `TokenType.PUNCTUATION`
- **AND** the concatenation of all token values SHALL equal the input

### Requirement: PythonLexer SHALL color f-string literal content as STRING

For f-strings tokenized by Python 3.12+ into `FSTRING_START`, `FSTRING_MIDDLE`, and `FSTRING_END` tokens, `PythonLexer` SHALL emit those parts as `TokenType.STRING`. Expression parts inside replacement fields SHALL be tokenized as ordinary Python tokens.

#### Scenario: f-string literal parts are STRING tokens

- **WHEN** `PythonLexer().tokenize` is called with `"msg = f\"hello {name}\"\n"`
- **THEN** the `f"`, `hello `, and closing `"` parts SHALL be emitted as `TokenType.STRING`
- **AND** `name` inside the replacement field SHALL be emitted as `TokenType.IDENTIFIER`
- **AND** the concatenation of all token values SHALL equal the input

### Requirement: PythonLexer SHALL classify soft keywords by context

`PythonLexer` SHALL NOT unconditionally color soft keywords as `KEYWORD`. `match` and `case` SHALL be emitted as `KEYWORD` only when the next significant token on the same logical line can begin a pattern (a NAME, STRING, or NUMBER token, where a NAME that is itself a keyword other than the literal-pattern keywords `None`/`True`/`False` cannot begin a pattern); otherwise they SHALL be emitted as `IDENTIFIER`. The identifiers `type` and `_` SHALL NOT be treated as keywords: `type` SHALL follow ordinary builtin classification and `_` SHALL be emitted as `IDENTIFIER`.

#### Scenario: match used as a variable

- **WHEN** `PythonLexer().tokenize("match = re.match(pattern, text)\n")` is called
- **THEN** both occurrences of `match` SHALL be emitted as `TokenType.IDENTIFIER`

#### Scenario: match used as a variable at the end of a statement

- **WHEN** `PythonLexer().tokenize("x = match\nprint(x)\n")` is called
- **THEN** `match` SHALL be emitted as `TokenType.IDENTIFIER`

#### Scenario: match statement keeps the keyword

- **WHEN** `PythonLexer().tokenize("match command:\n    case _: pass\n")` is called
- **THEN** the first `match` SHALL be emitted as `TokenType.KEYWORD`

#### Scenario: match used before a hard keyword

- **WHEN** `PythonLexer().tokenize("for match in re.finditer(pattern, text):\n    pass\n")` is called
- **THEN** `match` SHALL be emitted as `TokenType.IDENTIFIER`

#### Scenario: case literal patterns keep the keyword

- **WHEN** `PythonLexer().tokenize('match point:\n    case None: pass\n    case 1: pass\n    case "a": pass\n')` is called
- **THEN** `match` SHALL be emitted as `TokenType.KEYWORD`
- **AND** each `case` SHALL be emitted as `TokenType.KEYWORD`

#### Scenario: type builtin call

- **WHEN** `PythonLexer().tokenize("t = type(obj)\n")` is called
- **THEN** `type` SHALL be emitted as `TokenType.BUILTIN`

#### Scenario: throwaway underscore

- **WHEN** `PythonLexer().tokenize("for _ in range(3):\n    pass\n")` is called
- **THEN** `_` SHALL be emitted as `TokenType.IDENTIFIER`

### Requirement: PythonLexer SHALL recognize decorators only at statement start

`PythonLexer` SHALL treat `@` as starting a decorator only when it appears at the beginning of a logical line (start of input or immediately following a newline or indent). An `@` operator in expression position (matrix multiplication) SHALL NOT cause the following name to be classified as a decorator.

#### Scenario: Matrix multiplication is not a decorator

- **WHEN** `PythonLexer().tokenize("c = a @ b\n")` is called
- **THEN** no token SHALL be emitted as `TokenType.DECORATOR`
- **AND** `b` SHALL be emitted as `TokenType.IDENTIFIER`

#### Scenario: Line-start decorator still works

- **WHEN** `PythonLexer().tokenize("@property\ndef x(self): pass\n")` is called
- **THEN** `property` SHALL be emitted as `TokenType.DECORATOR`

### Requirement: TomlLexer SHALL match datetimes in strict RFC 3339 shape

`TomlLexer` SHALL recognize TOML dates and datetimes only when they match the RFC 3339-derived TOML shapes (`YYYY-MM-DD`, optionally followed by a time part `HH:MM:SS` with optional fractional seconds and optional offset). A date token SHALL NOT extend past the end of the datetime literal; trailing content on the same line (including comments) SHALL be tokenized separately.

#### Scenario: Date with trailing comment

- **WHEN** `TomlLexer().tokenize("d = 2024-01-01  # release date\n")` is called
- **THEN** a `Token(TokenType.STRING, "2024-01-01")` SHALL be emitted for the date
- **AND** a separate `Token(TokenType.COMMENT, "# release date")` SHALL be emitted

#### Scenario: Full datetime still matches

- **WHEN** `TomlLexer().tokenize("t = 2024-01-01T10:20:30Z\n")` is called
- **THEN** a single `Token(TokenType.STRING, "2024-01-01T10:20:30Z")` SHALL be emitted

### Requirement: TomlLexer SHALL recognize hexadecimal, octal, and binary integers

`TomlLexer` SHALL emit TOML hexadecimal (`0x`), octal (`0o`), and binary (`0b`) integer literals as `TokenType.NUMBER`, preserving the full literal including the prefix.

#### Scenario: Hexadecimal integer

- **WHEN** `TomlLexer().tokenize("mask = 0x10\n")` is called
- **THEN** a `Token(TokenType.NUMBER, "0x10")` SHALL be emitted

### Requirement: BashLexer SHALL yield special variables as single IDENTIFIER tokens

`BashLexer().tokenize` SHALL recognize positional and special shell parameters (`$0`–`$9`, `$@`, `$*`, `$#`, `$?`, `$-`, `$!`, `$$`) as variable references. For each reference, the lexer SHALL yield a single `Token(TokenType.IDENTIFIER, value)` whose value preserves the reference exactly as written, including the leading `$`.

#### Scenario: Positional parameter

- **WHEN** `BashLexer().tokenize("echo $1")` is called
- **THEN** the iterator SHALL yield a `Token(TokenType.IDENTIFIER, "$1")`
- **AND** it SHALL NOT yield a separate token whose value is `"$"` or `"1"`

### Requirement: BashLexer SHALL start comments only at line start or after whitespace

`BashLexer` SHALL treat `#` as starting a comment only when it appears at the beginning of a line or is immediately preceded by whitespace. A `#` inside an unquoted word SHALL NOT start a comment.

#### Scenario: Hash inside a word

- **WHEN** `BashLexer().tokenize("echo a#b\n")` is called
- **THEN** no `TokenType.COMMENT` token SHALL be emitted
- **AND** the concatenation of all token values SHALL equal the input

#### Scenario: Ordinary trailing comment

- **WHEN** `BashLexer().tokenize("echo a # b\n")` is called
- **THEN** a `Token(TokenType.COMMENT, "# b")` SHALL be emitted

