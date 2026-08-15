# Delta Spec: template-engine

## MODIFIED Requirements

### Requirement: render_markdown shall produce reactive Element trees from Markdown

`render_markdown(source: str, context: dict) -> ElementAbstract` SHALL render Markdown templates into reactive Element trees. The pipeline SHALL be: Markdown → HTML (via MarkdownPort) → strip directive paragraphs → parse HTML with multi-root support → bind → FragmentElement wrapping for multi-root. When Markdown produces a single top-level element, an `Element` SHALL be returned directly. When Markdown produces multiple top-level elements, a `FragmentElement` SHALL be returned containing all root elements.

`{% for %}` blocks whose body is a Markdown list (lines starting with `-`, `*`, `+`, or digit`.`/`)`) SHALL be routed to `MarkdownForElement` for merged single-`<ul>` output with collection-level reactivity (superseding the Change 6 baseline of one `<ul>` per iteration via `repeat()`). All other `{% for %}` blocks (headings, paragraphs, HTML blocks) SHALL continue to use the standard `repeat()` path (unchanged from Change 6).

#### Scenario: Basic Markdown rendering (single element)
- **WHEN** `render_markdown("# Hello {{ name }}", {"name": "World"})` is called
- **THEN** an `Element("h1", ..., [TextElement("Hello World")])` SHALL be returned

#### Scenario: Basic Markdown rendering (multiple elements)
- **WHEN** `render_markdown("# Title\n\nText.", ctx)` is called
- **THEN** a `FragmentElement([Element("h1", ...), Element("p", ...)])` SHALL be returned

#### Scenario: Component root usage with wrapper
- **WHEN** a developer returns `html.ARTICLE({}, render_markdown("..", ctx))` from a component setup
- **THEN** the FragmentElement SHALL render transparently inside `<article>`
- **AND** no extra `<div>` wrapper SHALL appear in the DOM

#### Scenario: Multi-root Markdown returned directly from a component setup
- **WHEN** a developer returns `render_markdown("# Title\n\nText.", ctx)` directly from a component setup (producing multiple top-level elements → `FragmentElement`)
- **THEN** the FragmentElement SHALL be accepted as the component's child content
- **AND** the fragment's children SHALL render inside the component's custom-element wrapper
- **AND** no component-root type error SHALL be raised

#### Scenario: {{ }} interpolation in Markdown
- **WHEN** `render_markdown("## {{ title }}", {"title": Signal("Home")})` is called
- **THEN** a reactive `TextElement(Signal("Home"))` SHALL be produced inside `<h2>`

#### Scenario: {% for %} over Markdown list body produces a single <ul> (supersedes Change 6 baseline of one `<ul>` per iteration via `repeat()`)
- **WHEN** source contains `{% for item in items %}\n- {{ item }}\n{% endfor %}`
- **THEN** the for-body SHALL be detected as a list body and routed to `MarkdownForElement`
- **AND** the rendered children SHALL contain a **single** `<ul>` element with N `<li>` children (merged)
- **AND** `<li>` content SHALL be reactive (fine-grained `TextElement` updates on field changes)
- **AND** appending/removing items to/from the iterable SHALL trigger a block re-render via `_refresh()`

#### Scenario: Component tags in Markdown HTML blocks
- **WHEN** source contains `<user-card title="Hello" />`
- **THEN** the component tag SHALL be preserved through Markdown parsing
- **AND** `render_template` SHALL resolve it via ComponentStore (Change 3)

#### Scenario: File-based Markdown via load_text composition
- **WHEN** a developer writes `render_markdown(await load_text("page.md"), ctx)` inside an async component setup
- **THEN** `load_text` SHALL read the file content and `render_markdown` SHALL parse the returned string
- **AND** on the server, the read SHALL be recorded for hydration; on the browser, the same call SHALL resolve from the payload
