## MODIFIED Requirements

### Requirement: render_markdown shall produce reactive Element trees from Markdown

`render_markdown(source: str | Path, context: dict) -> ElementAbstract` SHALL render Markdown templates into reactive Element trees. The pipeline SHALL be: Markdown → HTML (via MarkdownPort) → strip directive paragraphs → parse HTML with multi-root support → bind → FragmentElement wrapping for multi-root. When Markdown produces a single top-level element, an `Element` SHALL be returned directly. When Markdown produces multiple top-level elements, a `FragmentElement` SHALL be returned containing all root elements.

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

#### Scenario: Multi-root Markdown requires explicit wrapper as component root
- **WHEN** a developer returns `render_markdown("# Title\n\nText.", ctx)` directly from a component setup (producing multiple top-level elements → `FragmentElement`)
- **THEN** `Component.__init_component` SHALL raise `WebComPyException("Root Node of Component must be instance of 'Element'")` because the root is a `FragmentElement`, not an `Element`
- **AND** the developer SHALL wrap the result in an explicit root element (e.g., `html.ARTICLE({}, render_markdown(...))`)

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

#### Scenario: File loading
- **WHEN** `render_markdown(Path("page.md"), ctx)` is called in a server environment
- **THEN** the file SHALL be read, parsed as Markdown, and rendered

## ADDED Requirements

### Requirement: MarkdownForElement shall merge for-loop list bodies into a single block element

`MarkdownForElement` SHALL be a `DynamicElement` subclass in `webcompy/template/_markdown_for.py` that renders `{% for %}` blocks over Markdown list bodies as a single `<ul>` (or `<ol>`) with merged `<li>` children. It SHALL concatenate per-item Markdown text, render the merged text via `MarkdownPort`, bind the result via `_render_nodes`, and set the bound children as its child elements. The element SHALL follow `SwitchElement` lifecycle patterns for callback node management and async `_refresh`.

#### Scenario: Ordered list merging via MarkdownForElement
- **WHEN** `render_markdown("{% for item in items %}\n1. {{ item }}\n{% endfor %}", ctx)` is called
- **THEN** a single `<ol>` with merged `<li>` children SHALL be produced

#### Scenario: Field-level reactivity (no block re-render)
- **WHEN** a `{% for %}` list body contains `{{ item.name }}` where `item.name` is a `Signal`
- **THEN** changing `item.name.value` SHALL update the corresponding `TextElement` in the DOM fine-grained
- **AND** `MarkdownForElement._refresh` SHALL NOT be triggered (no collection change)

#### Scenario: Collection reactivity (block re-render)
- **WHEN** the iterable is a `ReactiveList` and a new item is appended
- **THEN** the `MarkdownForElement` SHALL re-render the entire merged block
- **AND** the `<ul>` SHALL contain the new item in its `<li>` children

### Requirement: Markdown for-expansion shall use expression-scoped loop-variable renaming

Per-item loop variable references in `{{ }}` SHALL be renamed with a per-iteration prefix (`__wmdf_{N}_{varname}`) scoped to template expressions only. The synthetic keys SHALL be injected into the binding context.

#### Scenario: Loop variable renamed per iteration
- **WHEN** `{% for item in items %}- {{ item.name }}{% endfor %}` is expanded with items=[obj0, obj1]
- **THEN** the per-item body SHALL emit `- {{ __wmdf_0_item.name }}` and `- {{ __wmdf_1_item.name }}`
- **AND** context SHALL contain `__wmdf_0_item = obj0` and `__wmdf_1_item = obj1`

#### Scenario: Renaming scoped to template expressions only
- **WHEN** the body Markdown prose contains the word "item" outside `{{ }}`
- **THEN** the prose SHALL NOT be renamed (only `{{ }}` / `{% %}` spans are renamed)

#### Scenario: Tuple unpacking
- **WHEN** `{% for k, v in my_dict %}- {{ k }}: {{ v }}{% endfor %}` is used
- **THEN** both `k` and `v` SHALL be renamed per iteration (`__wmdf_N_k`, `__wmdf_N_v`)
- **AND** both SHALL be available in the body context

### Requirement: List-body detection shall route for-loops to MarkdownForElement or repeat()

The `render_markdown` pipeline SHALL detect whether a `{% for %}` body is a list body (lines start with `-`, `*`, `+`, or digit+`.`/`)`) and route accordingly: list bodies → `MarkdownForElement`; non-list bodies → standard `repeat()`.

#### Scenario: List body detected and routed to MarkdownForElement
- **WHEN** a `{% for %}` body consists of lines starting with `-` or `*` or digit`.`/`)`
- **THEN** a `MarkdownForElement` SHALL be created

#### Scenario: Non-list body routed to repeat()
- **WHEN** a `{% for %}` body consists of heading lines (`#`), paragraphs (plain text), or HTML blocks (`<div>`)
- **THEN** the standard `repeat()` path from Change 6 SHALL be used (fully reactive with reactive `{% if %}`)

#### Scenario: Non-list for preserves reactive if
- **WHEN** a non-list `{% for %}` body contains `{% if item.show %}...{% endif %}`
- **THEN** the `{% if %}` SHALL be bound via `switch()` and SHALL reactively update on `item.show` change

### Requirement: Nested for-loops and if-in-for shall be handled in list-body for

Nested `{% for %}` inside a list-body `{% for %}` SHALL be recursively expanded. `{% if %}` inside a list-body `{% for %}` SHALL be statically evaluated per item during expansion.

#### Scenario: Nested for in list body
- **WHEN** a list-body `{% for %}` body contains another `{% for %}`
- **THEN** the inner `{% for %}` SHALL be recursively expanded as a nested `MarkdownForElement`
- **AND** naming SHALL be composite (`__wmdf_{outer}_{inner}_varname`)

#### Scenario: If-in-for static evaluation
- **WHEN** a list-body `{% for %}` body contains `{% if item.active %}- {{ item.name }}{% endif %}`
- **THEN** the `{% if %}` SHALL be evaluated statically per item during expansion
- **AND** if `item.active` is falsy for iteration N, that iteration's `- {{ item.name }}` SHALL NOT be emitted
- **AND** the if SHALL re-evaluate on collection change (block re-render)

#### Scenario: HTML-block escape hatch for reactive list-item conditional
- **WHEN** a developer needs reactive list-item conditionals
- **THEN** they SHALL use `<ul>{% for item in items %}{% if item.active %}<li>{{ item.name }}</li>{% endif %}{% endfor %}</ul>` (HTML block)
- **AND** this SHALL use `repeat()` + `switch()` for full reactivity

### Requirement: __wmdf_ prefix shall be reserved for framework-generated context keys

All synthetic context keys generated by Markdown for-expansion SHALL use the `__wmdf_` prefix. User-supplied context keys with this prefix MAY collide with framework-generated keys.

#### Scenario: Reserved prefix documented
- **WHEN** a developer reviews the template engine documentation
- **THEN** `__wmdf_` SHALL be listed as a reserved prefix for framework-generated context keys

### Requirement: MarkdownForElement shall re-render on collection change with lifecycle hooks deferred

When the iterable is reactive (`ReactiveList`/`ReactiveDict`), `MarkdownForElement` SHALL register an `on_after_updating` callback that triggers `_refresh()`. The `_refresh` SHALL defer `on_after_rendering` lifecycle hooks during reactivation (matching `SwitchElement` behavior). For synchronous invocation of `_refresh` from `on_after_updating` callbacks, `MarkdownForElement` SHALL use the shared `_run_refresh_sync` helper from `webcompy.elements.types._dynamic`, rather than duplicating the async-to-sync wrapper logic.

#### Scenario: Callback registered on reactive iterable
- **WHEN** `MarkdownForElement` renders with a `ReactiveList` iterable
- **THEN** an `on_after_updating` callback SHALL be registered on the `ReactiveList`
- **AND** the callback SHALL invoke `_refresh()`
- **AND** the callback node SHALL be stored in `_callback_nodes` and destroyed on element cleanup

#### Scenario: Static iterable skips callback registration
- **WHEN** `MarkdownForElement` renders with a plain `list` iterable
- **THEN** no `on_after_updating` callback SHALL be registered
- **AND** `_refresh` SHALL NOT be called on iterable change (block is static snapshot)

#### Scenario: on_after_rendering deferred during refresh
- **WHEN** `_refresh()` is triggered by a collection change (not initial render)
- **THEN** `on_after_rendering` lifecycle hooks SHALL be deferred via `start_defer_after_rendering` / `end_defer_after_rendering`
