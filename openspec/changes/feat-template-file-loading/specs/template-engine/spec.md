## ADDED Requirements

### Requirement: Template engine shall accept file paths as template source

`render_template(source: str | Path, context: dict[str, Any])` SHALL accept `pathlib.Path` objects as the source argument. The file SHALL be read and its content used as the template string.

#### Scenario: File loading on server
- **WHEN** `render_template(Path("templates/card.html"), ctx)` is called in a standard Python environment
- **THEN** the file SHALL be read using `Path.read_text(encoding="utf-8")`
- **AND** the file content SHALL be parsed as a template string

#### Scenario: File loading in browser
- **WHEN** `render_template(Path("templates/card.html"), ctx)` is called in a PyScript browser environment
- **THEN** `WebComPyException` SHALL be raised with a message recommending inline string templates

#### Scenario: Inline string unchanged
- **WHEN** `render_template("<div>{{ x }}</div>", ctx)` is called with a string source
- **THEN** behavior SHALL be identical to Change 1 (no regression)

### Requirement: File paths shall be resolved relative to the calling module

Relative `Path` arguments SHALL be resolved against the directory of the calling Python module.

#### Scenario: Relative path resolution
- **WHEN** `render_template(Path("templates/card.html"), ctx)` is called from `/app/components/page.py`
- **THEN** the file SHALL be searched at `/app/components/templates/card.html`

### Requirement: File reads shall not be cached

Template file content SHALL be read fresh on each `render_template` call. Only the parsed Template AST SHALL be cached by content string.

#### Scenario: File change during development
- **WHEN** a template file is modified between two `render_template` calls
- **THEN** the second call SHALL read the updated file content
