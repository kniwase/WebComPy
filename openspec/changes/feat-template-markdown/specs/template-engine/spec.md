## ADDED Requirements

### Requirement: DefaultMarkdownParser shall convert Markdown to HTML

`DefaultMarkdownParser.render(source)` SHALL convert Markdown text to HTML strings. `textwrap.dedent` SHALL be applied to the source before parsing.

#### Scenario: Headings
- **WHEN** source contains `# Title`, `## Section`, ... `###### Sub`
- **THEN** the output SHALL be `<h1>Title</h1>`, `<h2>Section</h2>`, ... `<h6>Sub</h6>`

#### Scenario: Paragraphs
- **WHEN** source contains consecutive non-blank lines
- **THEN** they SHALL be joined into `<p>text</p>` with inline formatting applied

#### Scenario: Unordered lists
- **WHEN** source contains `- item1` and `- item2`
- **THEN** the output SHALL be `<ul><li>item1</li><li>item2</li></ul>`

#### Scenario: Ordered lists
- **WHEN** source contains `1. first` and `2. second`
- **THEN** the output SHALL be `<ol><li>first</li><li>second</li></ol>`

#### Scenario: Nested lists
- **WHEN** source contains an indented list item under a parent item
- **THEN** a nested `<ul>` or `<ol>` SHALL be produced inside the parent `<li>`
- **AND** tabs SHALL be normalized to 2 spaces for indent calculation

#### Scenario: Fenced code blocks
- **WHEN** source contains lines between ```` ``` ```` fences
- **THEN** the output SHALL be `<pre><code>content</code></pre>`

#### Scenario: Inline formatting
- **WHEN** source contains `**bold**`, `*italic*`, `` `code` ``, `[link](url)`, `![img](url)`, `~~strike~~`
- **THEN** they SHALL be converted to `<strong>`, `<em>`, `<code>`, `<a href>`, `<img>`, `<del>` respectively

#### Scenario: Blockquotes
- **WHEN** source contains `> quoted text`
- **THEN** the output SHALL be `<blockquote>quoted text</blockquote>`

#### Scenario: Horizontal rules
- **WHEN** source contains `---`, `***`, or `___` on its own line
- **THEN** the output SHALL be `<hr>`

#### Scenario: HTML block passthrough
- **WHEN** lines start with `<` (HTML blocks)
- **THEN** they SHALL be preserved as-is in the output without Markdown processing
- **AND** component tags (`<user-card>`) SHALL pass through unchanged

### Requirement: render_markdown shall produce reactive Element trees from Markdown

`render_markdown(source: str | Path, context: dict) -> ElementAbstract` SHALL render Markdown templates into reactive Element trees. The pipeline SHALL be: Markdown → HTML (via MarkdownPort) → strip directive paragraphs → parse HTML with multi-root support → bind → FragmentElement wrapping for multi-root. When Markdown produces a single top-level element, an `Element` SHALL be returned directly. When Markdown produces multiple top-level elements, a `FragmentElement` SHALL be returned containing all root elements.

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

#### Scenario: Multi-root Markdown requires explicit wrapper as component root
- **WHEN** a developer returns `render_markdown("# Title\n\nText.", ctx)` directly from a component setup (producing multiple top-level elements → `FragmentElement`)
- **THEN** `Component.__init_component` SHALL raise `WebComPyException("Root Node of Component must be instance of 'Element'")` because the root is a `FragmentElement`, not an `Element`
- **AND** the developer SHALL wrap the result in an explicit root element (e.g., `html.ARTICLE({}, render_markdown(...))`)

#### Scenario: {{ }} interpolation in Markdown
- **WHEN** `render_markdown("## {{ title }}", {"title": Signal("Home")})` is called
- **THEN** a reactive `TextElement(Signal("Home"))` SHALL be produced inside `<h2>`

#### Scenario: {% for %} over Markdown list (baseline — one <ul> per iteration)
- **WHEN** source contains `{% for item in items %}\n- {{ item }}\n{% endfor %}`
- **THEN** the `{% for %}` and `{% endfor %}` SHALL NOT be wrapped in `<p>` tags
- **AND** the for-body `<ul><li>{{ item }}</li></ul>` SHALL be repeated via `repeat()`, producing one `<ul>` per iteration (baseline behavior)
- **AND** `{{ item }}` SHALL be reactive within each iteration
- **NOTE**: Merging into a single `<ul>` is deferred to Change 7 (`MarkdownForElement`)

#### Scenario: Component tags in Markdown HTML blocks
- **WHEN** source contains `<user-card title="Hello" />`
- **THEN** the component tag SHALL be preserved through Markdown parsing
- **AND** `render_template` SHALL resolve it via ComponentStore (Change 3)

#### Scenario: File loading
- **WHEN** `render_markdown(Path("page.md"), ctx)` is called in a server environment
- **THEN** the file SHALL be read, parsed as Markdown, and rendered

### Requirement: {% %} directives shall not be wrapped in paragraph tags

Line-by-line `{% %}` directives (e.g., `{% for item in items %}`) that would be wrapped in `<p>` tags by the Markdown parser SHALL have those `<p>` wrappers removed before passing to `render_template`.

#### Scenario: {% for %} directive unwrapped
- **WHEN** Markdown processing produces `<p>{% for item in items %}</p>`
- **THEN** the `<p>` wrapper SHALL be stripped to `{% for item in items %}`

#### Scenario: {% if %} with text preserved
- **WHEN** Markdown produces `<p>{% if x %}visible text{% endif %}</p>`
- **THEN** the `<p>` SHALL NOT be stripped (directive has sibling text content)
