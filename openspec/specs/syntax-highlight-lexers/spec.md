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

`Lexer.tokenize(code)` SHALL yield `Token` objects in the order they appear in the source code. The combined `value` of consecutive tokens of the same `type` MAY be merged by the implementation, but the visible output SHALL be identical to a sequence of distinct tokens.

#### Scenario: Token order matches source order

- **WHEN** `PythonLexer().tokenize("a + b")` is called
- **THEN** the iterator SHALL yield `a`, `+`, `b` (and any whitespace tokens) in that order
- **AND** no token SHALL be yielded out of order

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

`BashLexer().tokenize` SHALL recognize shell variable references of the form `$NAME` and `${NAME}` (where `NAME` matches `[A-Za-z_][A-Za-z0-9_]*`). For each reference, the lexer SHALL yield a single `Token(TokenType.IDENTIFIER, "NAME")` token — the leading `$` and (for the braced form) the surrounding braces SHALL be stripped from the `value`.

#### Scenario: Bare variable reference

- **WHEN** `BashLexer().tokenize("echo $HOME")` is called
- **THEN** the iterator SHALL yield a `Token(TokenType.IDENTIFIER, "HOME")`
- **AND** it SHALL NOT yield any token whose `value` is `"$HOME"`

#### Scenario: Braced variable reference

- **WHEN** `BashLexer().tokenize("echo ${PATH}")` is called
- **THEN** the iterator SHALL yield a `Token(TokenType.IDENTIFIER, "PATH")`
- **AND** it SHALL NOT yield any token whose `value` is `"${PATH}"`

