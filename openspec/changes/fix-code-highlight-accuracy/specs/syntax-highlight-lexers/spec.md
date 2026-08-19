# fix-code-highlight-accuracy delta for syntax-highlight-lexers

## MODIFIED Requirements

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

## ADDED Requirements

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

### Requirement: PythonLexer SHALL classify operator tokens as PUNCTUATION with same-type merging

`PythonLexer` SHALL emit Python `OP` tokens as `TokenType.PUNCTUATION`. Consecutive `PUNCTUATION` tokens with no intervening source text MAY be merged into a single token whose value is the concatenation; the merged output SHALL be textually identical to the unmerged sequence.

#### Scenario: def statement token positions

- **WHEN** `PythonLexer().tokenize("def foo(): pass")` is called
- **THEN** the first token SHALL be `Token(TokenType.KEYWORD, "def")`
- **AND** the third token SHALL be `Token(TokenType.FUNCTION, "foo")`
- **AND** the fifth token SHALL be `Token(TokenType.PUNCTUATION, ":")`

#### Scenario: Merged punctuation preserves text

- **WHEN** `PythonLexer().tokenize("x = a[0] + f(b, c)")` is called
- **THEN** the concatenation of all token values SHALL equal the input
- **AND** every `,`, `(`, `)`, `[`, `]`, `+` character SHALL be contained in a `PUNCTUATION` token

### Requirement: PythonLexer SHALL color f-string literal content as STRING

For f-strings tokenized by Python 3.12+ into `FSTRING_START`, `FSTRING_MIDDLE`, and `FSTRING_END` tokens, `PythonLexer` SHALL emit those parts as `TokenType.STRING`. Expression parts inside replacement fields SHALL be tokenized as ordinary Python tokens.

#### Scenario: f-string literal parts are STRING tokens

- **WHEN** `PythonLexer().tokenize` is called with `"msg = f\"hello {name}\"\n"`
- **THEN** the `f"`, `hello `, and closing `"` parts SHALL be emitted as `TokenType.STRING`
- **AND** `name` inside the replacement field SHALL be emitted as `TokenType.IDENTIFIER`
- **AND** the concatenation of all token values SHALL equal the input

### Requirement: PythonLexer SHALL classify soft keywords by context

`PythonLexer` SHALL NOT unconditionally color soft keywords as `KEYWORD`. `match` and `case` SHALL be emitted as `KEYWORD` only when the next significant token can begin a pattern (a NAME, STRING, or NUMBER token); otherwise they SHALL be emitted as `IDENTIFIER`. The identifiers `type` and `_` SHALL NOT be treated as keywords: `type` SHALL follow ordinary builtin classification and `_` SHALL be emitted as `IDENTIFIER`.

#### Scenario: match used as a variable

- **WHEN** `PythonLexer().tokenize("match = re.match(pattern, text)\n")` is called
- **THEN** both occurrences of `match` SHALL be emitted as `TokenType.IDENTIFIER`

#### Scenario: match statement keeps the keyword

- **WHEN** `PythonLexer().tokenize("match command:\n    case _: pass\n")` is called
- **THEN** the first `match` SHALL be emitted as `TokenType.KEYWORD`

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
