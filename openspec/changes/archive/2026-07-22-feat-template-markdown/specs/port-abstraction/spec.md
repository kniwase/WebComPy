## ADDED Requirements

### Requirement: MarkdownPort ABC shall exist

The system SHALL provide a `MarkdownPort` abstract base class in `webcompy.ports` with a single abstract method `render(source: str) -> str` that converts Markdown text to HTML.

#### Scenario: MarkdownPort is importable
- **WHEN** a developer imports `webcompy.ports`
- **THEN** `MarkdownPort` SHALL be accessible

#### Scenario: MarkdownPort cannot be instantiated directly
- **WHEN** a developer attempts to instantiate `MarkdownPort` directly
- **THEN** Python SHALL raise `TypeError` due to abstract method `render`

#### Scenario: BrowserRenderContext provides default MarkdownPort
- **WHEN** a `BrowserRenderContext` is created
- **THEN** `MARKDOWN_PORT_KEY` SHALL be provided with a `DefaultMarkdownParser` instance

#### Scenario: ServerRenderContext provides default MarkdownPort
- **WHEN** a `ServerRenderContext` is created
- **THEN** `MARKDOWN_PORT_KEY` SHALL be provided with a `DefaultMarkdownParser` instance

#### Scenario: Custom parser injection
- **WHEN** a user calls `app.provide(MARKDOWN_PORT_KEY, CustomParser())`
- **THEN** `inject(MARKDOWN_PORT_KEY)` SHALL return the custom parser instance
