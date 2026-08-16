# syntax-highlight-lexers — Bash Variable Reference Correction Deltas

## MODIFIED Requirements

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
