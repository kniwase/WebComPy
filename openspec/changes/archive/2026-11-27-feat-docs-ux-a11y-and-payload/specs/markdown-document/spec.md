# Spec Delta

## ADDED Requirements

### Requirement: Document mode SHALL support opt-in clickable heading anchor links without altering TOC text

`load_markdown_document()` SHALL support an opt-in `heading_anchors: bool = False` (or document transform option) that appends a clickable permalink anchor (`<a class="heading-anchor" href="#{id}">`) inside `<h2>`–`<h6>` heading elements that carry an `id`, styled subtly in `prose.css` (within `@layer prose`). Heading TOC extraction (`MarkdownDocument.toc`) SHALL resolve clean heading text excluding anchor link glyphs so TOC labels are never polluted with `#`.

#### Scenario: Heading anchor link added without polluting TOC

- **WHEN** `load_markdown_document()` renders a Markdown heading `## Reactive Signals` with heading anchors enabled
- **THEN** the rendered `<h2>` carries `id="reactive-signals"` and a clickable `<a class="heading-anchor" href="#reactive-signals">` child
- **AND** `MarkdownDocument.toc` records text `"Reactive Signals"` without a trailing `"#"`
