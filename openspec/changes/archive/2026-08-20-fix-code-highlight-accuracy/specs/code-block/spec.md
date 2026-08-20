# fix-code-highlight-accuracy delta for code-block

## MODIFIED Requirements

### Requirement: The framework SHALL ship built-in lexers for Python, Bash, and TOML

The framework SHALL ship three built-in lexers that are registered automatically on `webcompy.ui.code_block` import: `PythonLexer`, `BashLexer`, and `TomlLexer`. The `PythonLexer` SHALL be based on the standard library `tokenize` module.

#### Scenario: Python code is tokenized with tokenize

- **WHEN** `PythonLexer().tokenize("def foo(): pass")` is called
- **THEN** the first token SHALL be `Token(TokenType.KEYWORD, "def")`
- **AND** the third token SHALL be `Token(TokenType.FUNCTION, "foo")` (the function name following `def`)
- **AND** the tokens for `(`, `)`, and `:` SHALL be `TokenType.PUNCTUATION`

#### Scenario: Bash code is tokenized with regex

- **WHEN** `BashLexer().tokenize("echo $VAR")` is called
- **THEN** the tokens SHALL include `Token(TokenType.BUILTIN, "echo")` and `Token(TokenType.IDENTIFIER, "$VAR")`

The `$` prefix is preserved in the token value so the rendered HTML faithfully displays the variable syntax (`echo $HOME`, not `echo HOME`). For braced variables, the full `${NAME}` form is preserved (`Token(TokenType.IDENTIFIER, "${PATH}")`).

#### Scenario: TOML code is tokenized with regex

- **WHEN** `TomlLexer().tokenize('[section]\nkey = "value"')` is called
- **THEN** the tokens SHALL include `Token(TokenType.IDENTIFIER, "[section]")`, `Token(TokenType.IDENTIFIER, "key")`, and `Token(TokenType.STRING, "\"value\"")`
