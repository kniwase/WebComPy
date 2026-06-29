# code-block Specification

## Purpose
TBD - created by archiving change feat-ui-toolkit-foundation. Update Purpose after archive.
## Requirements
### Requirement: The framework SHALL provide a `CodeBlock` component

The framework SHALL provide a `webcompy.ui.code_block.CodeBlock` component that accepts `code: str | Signal[str]` and `lang: str` props and renders the code inside `<pre><code class="language-{lang}">...</code></pre>`, with the code tokenized into `<span class="...">` elements by the registered lexer for `lang`.

#### Scenario: Rendering a static code block

- **WHEN** a component template includes `CodeBlock({"code": "def foo(): pass", "lang": "python"})`
- **THEN** the rendered HTML SHALL contain `<pre><code class="language-python">`
- **AND** the code content SHALL be wrapped in `<span class="tok-kw k">def</span>` and similar token spans
- **AND** the rendered HTML SHALL be identical between SSR and CSR

#### Scenario: Rendering a dynamic code block

- **WHEN** `CodeBlock` receives `code: Signal[str]` and the signal's value is updated after initial render
- **THEN** the displayed highlighted HTML SHALL update to reflect the new value
- **AND** the update SHALL happen in pure Python (no client-side JavaScript required)

### Requirement: The framework SHALL provide a `highlight(code, lang)` function

The framework SHALL provide a `webcompy.ui.code_block.highlight(code: str, lang: str) -> str` function that returns a string of HTML token spans for the given code and language. The function SHALL escape HTML in token values to prevent injection.

#### Scenario: Calling highlight directly

- **WHEN** a developer calls `highlight("print('hi')", "python")`
- **THEN** the function SHALL return an HTML string containing token spans
- **AND** any `<`, `>`, `&`, and quote characters in the input SHALL be HTML-escaped

#### Scenario: Unknown language falls back to a single tok-ident span

- **WHEN** `highlight(code, "nonexistent-language")` is called
- **THEN** the function SHALL return a single `<span class="tok-ident">` element containing the code HTML-escaped
- **AND** the function SHALL NOT raise `LexerNotFoundError`
- **AND** the fallback SHALL also apply when a registered lexer returns no tokens for the given code

This graceful fallback prevents an unknown `lang` from crashing the entire page render. The `LexerNotFoundError` exception is still raised by `get_lexer` for callers that need to surface the error programmatically; `highlight` is the user-facing convenience that opts into the fallback.

### Requirement: The framework SHALL emit dual class names for Pygments compatibility

The framework SHALL emit both semantic class names (e.g., `tok-kw`, `tok-str`) and Pygments short class names (e.g., `k`, `s`) on each `<span>` so that the rendered HTML is styleable by either the framework's design-token CSS or any Pygments stylesheet.

#### Scenario: A token has a Pygments short class

- **WHEN** a Python keyword token is rendered
- **THEN** the `<span>` element SHALL have class `tok-kw k` (in that order)
- **AND** the framework's CSS rule `.tok-kw { color: var(--tok-kw); }` SHALL apply
- **AND** a Pygments stylesheet rule `.k { color: ...; }` SHALL also apply if loaded

#### Scenario: An identifier has no Pygments short class

- **WHEN** a generic identifier token is rendered
- **THEN** the `<span>` element SHALL have only the `tok-ident` class
- **AND** no `.x` (or similar) Pygments short class SHALL be present

### Requirement: The framework SHALL provide a `TokenType` enum

The framework SHALL provide a `webcompy.ui.code_block.TokenType` enum with values `KEYWORD`, `STRING`, `NUMBER`, `COMMENT`, `FUNCTION`, `BUILTIN`, `DECORATOR`, `OPERATOR`, `PUNCTUATION`, and `IDENTIFIER`. Each value's string form is used as the `tok-*` class name suffix.

#### Scenario: TokenType values map to class names

- **WHEN** a `Token(type=TokenType.KEYWORD, value="def")` is rendered
- **THEN** the resulting `<span>` SHALL have class `tok-kw`
- **AND** the mapping SHALL be derived from the enum's value (`"kw"`), not hardcoded

### Requirement: The framework SHALL provide a `Token` dataclass

The framework SHALL provide a `webcompy.ui.code_block.Token` frozen dataclass with `type: TokenType` and `value: str` fields. The dataclass SHALL be hashable and immutable.

#### Scenario: Token immutability

- **WHEN** a `Token` instance is created
- **THEN** attempting to assign to `token.type` or `token.value` SHALL raise `dataclasses.FrozenInstanceError`

### Requirement: The framework SHALL provide a `Lexer` protocol

The framework SHALL provide a `webcompy.ui.code_block.Lexer` `Protocol` with:
- A `name: ClassVar[str]` attribute (primary language identifier)
- An optional `aliases: ClassVar[tuple[str, ...]]` attribute (alternative names)
- An optional `file_extensions: ClassVar[tuple[str, ...]]` attribute
- A `tokenize(self, code: str) -> Iterator[Token]` method

#### Scenario: A custom lexer satisfies the protocol

- **WHEN** a developer defines a class with `name = "mydsl"`, `aliases = ("myd",)`, and a `tokenize(self, code) -> Iterator[Token]` method
- **AND** registers it via `register_lexer(MyDSLLexer())`
- **THEN** the framework SHALL accept it as a valid `Lexer`
- **AND** `get_lexer("mydsl")` and `get_lexer("myd")` SHALL return the same instance

### Requirement: The framework SHALL provide a lexer registry with name, alias, and file-extension lookup

The framework SHALL provide `register_lexer(lexer)`, `get_lexer(name)`, and `list_lexers()` functions. `get_lexer` SHALL look up the requested name as (in order) a primary name, an alias, or a file extension. `list_lexers` SHALL return a list of `LexerInfo` records.

#### Scenario: Registering a duplicate raises an error

- **WHEN** a developer calls `register_lexer(SomeLexer())` and another lexer with the same `name` is already registered
- **THEN** the call SHALL raise `ValueError`
- **UNLESS** `register_lexer(lexer, override=True)` is used, in which case the existing lexer is replaced

#### Scenario: Listing registered lexers

- **WHEN** a developer calls `list_lexers()`
- **THEN** the function SHALL return a list of `LexerInfo` records with the name, aliases, file extensions, and source ("builtin", "pygments", or "custom") of every registered lexer

### Requirement: The framework SHALL ship built-in lexers for Python, Bash, and TOML

The framework SHALL ship three built-in lexers that are registered automatically on `webcompy.ui.code_block` import: `PythonLexer`, `BashLexer`, and `TomlLexer`. The `PythonLexer` SHALL be based on the standard library `tokenize` module.

#### Scenario: Python code is tokenized with tokenize

- **WHEN** `PythonLexer().tokenize("def foo(): pass")` is called
- **THEN** the first token SHALL be `Token(TokenType.KEYWORD, "def")`
- **AND** the third token SHALL be `Token(TokenType.FUNCTION, "foo")` (the function name following `def`)
- **AND** the fifth token SHALL be `Token(TokenType.PUNCTUATION, ":")`

#### Scenario: Bash code is tokenized with regex

- **WHEN** `BashLexer().tokenize("echo $VAR")` is called
- **THEN** the tokens SHALL include `Token(TokenType.BUILTIN, "echo")` and `Token(TokenType.IDENTIFIER, "VAR")`

#### Scenario: TOML code is tokenized with regex

- **WHEN** `TomlLexer().tokenize('[section]\nkey = "value"')` is called
- **THEN** the tokens SHALL include `Token(TokenType.IDENTIFIER, "[section]")`, `Token(TokenType.IDENTIFIER, "key")`, and `Token(TokenType.STRING, "\"value\"")`

### Requirement: The framework SHALL provide a Pygments adapter skeleton

The framework SHALL provide a file at `webcompy/ui/code_block/lexers/_adapters/_pygments.py` containing a `PygmentsLexerWrapper` class and a `register_pygments_lexer(name)` function. The file SHALL NOT be imported by any other framework module. Adopting Pygments SHALL be a deliberate opt-in by the application.

#### Scenario: Pygments is not a hard dependency

- **WHEN** an application uses `webcompy.ui.code_block` without installing Pygments
- **THEN** the framework SHALL import successfully
- **AND** the built-in lexers SHALL be available

#### Scenario: Pygments can be adopted without API changes

- **WHEN** an application installs Pygments and calls `from webcompy.ui.code_block.lexers._adapters._pygments import register_pygments_lexer; register_pygments_lexer("javascript")`
- **THEN** a JavaScript lexer backed by Pygments SHALL be available via `get_lexer("javascript")`
- **AND** no changes to the `CodeBlock` public API SHALL be required

