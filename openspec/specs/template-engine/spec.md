# Template Engine

## Purpose

WebComPy provides an HTML template engine that parses template strings into reactive WebComPy Element trees using the stdlib `html.parser.HTMLParser`. This enables developers to define component UIs with familiar HTML syntax and `{{ varname }}` interpolation instead of the verbose Python element API (`html.DIV({...}, ...)`), while preserving the framework's reactive model — Signal references in text and attribute positions flow into the existing `TextElement` and `Computed`-valued attribute pipelines unchanged.

The template engine is the foundation for a family of related capabilities (control flow, component tags, file loading, CSS text, markdown) that reuse its parser, binder, and shared `_holes.py` interpolation utilities.

## Requirements

### Requirement: Template engine shall parse HTML strings into Element trees

`render_template(source: str, context: dict[str, Any]) -> Element` SHALL parse HTML template strings and return WebComPy `Element` trees using `html.parser.HTMLParser`. The returned value SHALL be a single `Element` instance suitable as a component root.

#### Scenario: Basic HTML structure
- **WHEN** `render_template("<div><p>Hello</p></div>", {})` is called
- **THEN** it SHALL return `Element("div", {}, children=[Element("p", {}, [TextElement("Hello")])])`

#### Scenario: Single root element only
- **WHEN** the template has multiple top-level elements (`<div></div><div></div>`)
- **THEN** `WebComPyException` SHALL be raised with message "Template must have exactly one root element"

#### Scenario: Whitespace around root element
- **WHEN** the template has whitespace-only text nodes before or after the root element
- **THEN** those whitespace nodes SHALL be skipped and the root element SHALL be returned

#### Scenario: Leading/trailing non-whitespace text
- **WHEN** the template has non-whitespace text before or after the root element (e.g., `"text<div></div>text"`)
- **THEN** `WebComPyException` SHALL be raised

### Requirement: Template engine shall handle void elements and self-closing tags

The template engine SHALL correctly handle void HTML elements (which have no end tag) and self-closing tag syntax.

#### Scenario: Void elements without closing slash
- **WHEN** the template contains `<br>`, `<img src="x">`, `<input type="text">`
- **THEN** the tree builder SHALL NOT push void elements onto the element stack
- **AND** `<br>` SHALL produce `NewLine()` not `Element("br")`
- **AND** `<img>`, `<input>` SHALL produce `Element` instances with their attributes

#### Scenario: Self-closing tags
- **WHEN** the template contains `<img src="x" />` with trailing slash
- **THEN** the element SHALL be created via `handle_startendtag` and SHALL NOT be pushed onto the stack

### Requirement: Template engine shall handle boolean attributes

Boolean HTML attributes (e.g., `disabled`, `checked`) that have no value SHALL be converted to `True` for the attribute dict.

#### Scenario: Boolean attribute conversion
- **WHEN** the template contains `<input disabled>`
- **THEN** the attribute SHALL be `{"disabled": True}` (which `_proc_attr` converts to `""` in the DOM)

#### Scenario: Boolean attribute with explicit value
- **WHEN** the template contains `<input disabled="disabled">`
- **THEN** the attribute SHALL be `{"disabled": "disabled"}` (string value preserved)

### Requirement: Template engine shall skip HTML comments

HTML comments (`<!-- ... -->`) SHALL be ignored and SHALL NOT produce any nodes in the Element tree.

#### Scenario: Comment skipping
- **WHEN** the template contains `<!-- this is a comment -->`
- **THEN** no node SHALL be created for the comment

### Requirement: Template engine shall reject CDATA content elements

`<script>`, `<style>`, `<iframe>`, `<noembed>`, `<noframes>`, and `<xmp>` tags SHALL be rejected with a `WebComPyException`.

#### Scenario: Script tag rejection
- **WHEN** the template contains `<script>alert(1)</script>`
- **THEN** `WebComPyException` SHALL be raised with a message recommending `scoped_style` or `raw_html` as alternatives

#### Scenario: Style tag rejection
- **WHEN** the template contains `<style>body{color:red}</style>`
- **THEN** `WebComPyException` SHALL be raised

### Requirement: Template engine shall support variable interpolation in text content

`{{ varname }}` and `{{ a.b.c }}` (dot notation) SHALL interpolate variables from the context into text content. Signal values SHALL be passed directly to `TextElement` for reactive updates.

#### Scenario: Signal in text content
- **WHEN** `render_template("<p>{{ count }}</p>", {"count": Signal(5)})` is called
- **THEN** `TextElement(Signal(5))` SHALL be created, preserving reactive binding

#### Scenario: String in text content
- **WHEN** `render_template("<p>{{ name }}</p>", {"name": "Alice"})` is called
- **THEN** `TextElement("Alice")` SHALL be created

#### Scenario: Element as variable
- **WHEN** `render_template("<div>{{ card }}</div>", {"card": Element("span", {}, [TextElement("x")])})` is called
- **THEN** the `Element("span")` SHALL be placed as a direct child of the `<div>`

#### Scenario: Component as variable
- **WHEN** a context variable contains a `Component` instance
- **THEN** the Component SHALL be placed as a direct child in the Element tree

#### Scenario: Missing variable
- **WHEN** a template references `{{ undefined_var }}` that is not in the context
- **THEN** `KeyError` SHALL be raised with a message listing the available variable names

#### Scenario: None variable
- **WHEN** a context variable is `None`
- **THEN** nothing SHALL be inserted at that position

#### Scenario: Dot notation with dict
- **WHEN** `{{ user.name }}` is used with `user` being `{"name": "Alice"}`
- **THEN** dict key access SHALL resolve `user["name"]` → `"Alice"`

#### Scenario: Dot notation with object attribute
- **WHEN** `{{ user.name }}` is used with `user` being a dataclass/NamedTuple
- **THEN** `getattr(user, "name")` SHALL be used

### Requirement: Template engine shall resolve non-HTML tags as components via ComponentStore

Tags not in the `HtmlTags` literal SHALL be resolved as component references. The component name SHALL be converted from kebab-case to PascalCase and looked up in the DI-accessible `ComponentStore`.

#### Scenario: Component tag resolution
- **WHEN** `<user-card>` is used and `UserCard` is registered in the ComponentStore
- **THEN** the `UserCard` component SHALL be instantiated and embedded as a child element

#### Scenario: Component not found with hyphen
- **WHEN** `<my-widget>` is used but no component matches in ComponentStore
- **THEN** `WebComPyException` SHALL be raised with a message that includes the looked-up component name, the available component names, and guidance that component tags require PascalCase component function names (kebab-case tag `<my-widget>` resolves to `MyWidget`)

#### Scenario: Unknown tag without hyphen
- **WHEN** `<widget>` is used and not found in ComponentStore or HtmlTags
- **THEN** the tag SHALL be treated as a regular HTML element (`Element("widget", ...)`)

#### Scenario: Self-closing component tag
- **WHEN** `<user-card title="Hi" />` is used with self-closing syntax
- **THEN** the component SHALL be instantiated with no default slot content

#### Scenario: HTML tags unaffected
- **WHEN** `<div>`, `<p>`, `<span>`, etc. are used
- **THEN** they SHALL continue to be treated as HTML elements (no ComponentStore lookup)

### Requirement: Component tags shall support static and dynamic props

Component attributes SHALL be converted to component props. Plain attributes SHALL be literal strings. `:`-prefixed attributes SHALL be variable references from the context.

#### Scenario: Static prop
- **WHEN** `<user-card title="Hello">` is used
- **THEN** `props = {"title": "Hello"}` SHALL be passed to the component

#### Scenario: Dynamic prop with Signal
- **WHEN** `<user-card :count="my_count">` is used and `my_count` is a Signal
- **THEN** `props = {"count": context["my_count"]}` SHALL be passed (Signal preserved for reactivity)

#### Scenario: Prop name kebab to snake_case conversion
- **WHEN** `<user-card :item-count="items">` is used
- **THEN** the prop name SHALL be converted from `item-count` to `item_count` in the props dict

#### Scenario: Interpolation in component attribute with Signal
- **WHEN** `<user-card title="Hello {{ name }}">` is used with `name` being a `Signal`
- **THEN** `resolve_attr` SHALL be called on the attribute parts
- **AND** a `Computed` SHALL be generated and passed as `props["title"]`
- **AND** the prop SHALL update reactively when the Signal changes

#### Scenario: Interpolation in component attribute without Signal
- **WHEN** `<user-card title="Hello {{ name }}">` is used with `name` being `"Alice"`
- **THEN** the prop value SHALL be the static string `"Hello Alice"`

### Requirement: Component body shall be passed as default slot

The children of a component tag SHALL be parsed and passed as the default slot content.

#### Scenario: Default slot
- **WHEN** `<user-card title="Hi"><p>Content</p></user-card>` is used
- **THEN** `slots = {"default": lambda: Element("p", {}, [TextElement("Content")])}` SHALL be passed

#### Scenario: Multiple children in default slot
- **WHEN** the component body has multiple elements
- **THEN** they SHALL be wrapped in a `FragmentElement` within the slot generator

### Requirement: Template engine shall support variable interpolation in attribute values

`{{ varname }}` in attribute values SHALL produce reactive `Computed` signals when the referenced variable is a `SignalBase`. When no Signal is referenced, static string evaluation SHALL be used.

#### Scenario: Single Signal in attribute
- **WHEN** `class="{{ cls }}"` is used with `cls` being `Signal("active")`
- **THEN** a `Computed` SHALL be generated that evaluates to `str(cls.value)`
- **AND** the `Computed` SHALL be passed as the attribute value
- **AND** the DOM attribute SHALL update reactively when `cls` changes

#### Scenario: Mixed literal and Signal
- **WHEN** `class="card {{ cls }}"` is used with `cls` being `Signal("active")`
- **THEN** a `Computed` SHALL be generated that evaluates to `f"card {cls.value}"`
- **AND** the attribute SHALL update reactively when `cls` changes

#### Scenario: Multiple Signals in one attribute
- **WHEN** `data-label="{{ a }} {{ b }}"` is used with both `a` and `b` being Signals
- **THEN** a single `Computed` SHALL be generated that depends on both Signals
- **AND** the attribute SHALL update when either Signal changes

#### Scenario: No Signal in attribute (static)
- **WHEN** `class="{{ cls }}"` is used with `cls` being `"static-string"` (plain str)
- **THEN** static string evaluation SHALL be used (no `Computed` created)
- **AND** the attribute value SHALL be `"static-string"`

#### Scenario: Integer in attribute (static)
- **WHEN** `data-index="{{ idx }}"` is used with `idx` being `42`
- **THEN** the resolved attribute SHALL be `"42"` (static, no Computed)

#### Scenario: Mixed literal and non-Signal variable
- **WHEN** `class="card {{ cls }}"` is used with `cls` being `"active"` (plain str)
- **THEN** the resolved attribute value SHALL be `"card active"` (static)

#### Scenario: None variable in attribute hole
- **WHEN** `class="{{ cls }}"` is used with `cls` being `None` or `Signal(None)`
- **THEN** the attribute SHALL be rendered as the empty string `""`
- **AND** for `Signal(None)`, a `Computed` SHALL be generated that evaluates to `""` and updates reactively
- **AND** for `class="card {{ cls }}"` with `cls=None`, the resolved attribute SHALL be `"card "` (literal prefix preserved, hole rendered as empty)

### Requirement: Template engine shall support event handler binding

`@event_name="handler_var"` attributes SHALL resolve the named callable from the context and set it as a DOM event handler.

#### Scenario: Click handler
- **WHEN** `render_template('<button @click="on_click">Btn</button>', {"on_click": handler})` is called
- **THEN** the resulting `Element` SHALL have `events={"click": handler}`

#### Scenario: Missing event handler
- **WHEN** `@click="missing_handler"` references a name not in the context
- **THEN** `KeyError` SHALL be raised

#### Scenario: `{{ }}` interpolation in `@event` value
- **WHEN** `@click="{{ handler }}"` references a handler name via `{{ }}` interpolation
- **THEN** `WebComPyException` SHALL be raised at bind time with a message indicating that `{{ }}` interpolation is not supported in `@event` attributes

#### Scenario: Non-callable `@event` handler value
- **WHEN** `@click="handler_var"` resolves to a non-callable value (e.g., an integer or string)
- **THEN** `WebComPyException` SHALL be raised at bind time with a message indicating the handler is not callable and listing the observed type

### Requirement: Template engine shall support DomNodeRef binding

`:ref="ref_var"` attributes SHALL resolve the named `DomNodeRef` from the context and set it as the element's ref.

#### Scenario: Ref binding
- **WHEN** `render_template('<input :ref="my_ref">', {"my_ref": DomNodeRef()})` is called
- **THEN** the resulting `Element` SHALL have `ref=my_ref`

#### Scenario: `{{ }}` interpolation in `:ref` value
- **WHEN** `:ref="{{ ref_var }}"` references a ref name via `{{ }}` interpolation
- **THEN** `WebComPyException` SHALL be raised at bind time with a message indicating that `{{ }}` interpolation is not supported in `:ref` attributes

### Requirement: Template engine shall accept locals() as context

The `context` dict argument SHALL accept the result of `locals()` called within a component setup function, enabling implicit variable capture.

#### Scenario: locals() usage
- **WHEN** `render_template("<p>{{ count }}</p>", locals())` is called from a component setup where `count = use_state(lambda: 0)` exists
- **THEN** `count` SHALL be accessible from the template

### Requirement: Template engine shall cache compiled Template ASTs

Template strings SHALL be parsed into Template ASTs and cached by source string. Subsequent calls with the same source SHALL reuse the cached AST.

#### Scenario: Cache hit
- **WHEN** `render_template` is called twice with the same template string
- **THEN** parsing SHALL occur only on the first call; the second call SHALL reuse the cached AST

### Requirement: Template engine shall apply textwrap.dedent

Template strings SHALL have `textwrap.dedent` applied before parsing to normalize indentation from triple-quoted Python strings.

#### Scenario: Dedent application
- **WHEN** a template string has leading whitespace from Python indentation
- **THEN** `textwrap.dedent` SHALL remove common leading whitespace before parsing

### Requirement: Template engine shall treat unknown tags leniently

Tags not in the HtmlTags literal SHALL be treated as regular HTML elements. An exception applies for hyphenated tags: tags containing a hyphen (`-`) that are not found in the ComponentStore SHALL raise a `WebComPyException` (see component tag resolution below). Non-hyphenated unknown tags SHALL NOT raise an error.

#### Scenario: Unknown non-hyphenated tag
- **WHEN** the template contains `<widget>text</widget>` and "widget" is not in HtmlTags or ComponentStore
- **THEN** `Element("widget", {}, [TextElement("text")])` SHALL be created

#### Scenario: Unknown hyphenated tag
- **WHEN** the template contains `<my-widget>text</my-widget>` and "MyWidget" is not registered in ComponentStore
- **THEN** `WebComPyException` SHALL be raised with a message listing available component names

### Requirement: FragmentElement shall render multiple children transparently without a DOM wrapper

`FragmentElement` SHALL be a `DynamicElement` subclass that has no DOM node of its own and renders its children sequentially in the parent element. After `refactor-element-foundations` (which widens the child-node type alias to `ElementAbstract`), `FragmentElement` is automatically valid as `ElementChildren` without a separate type-alias addition.

#### Scenario: Fragment renders children in parent
- **WHEN** a `FragmentElement([Element("p", {}, []), Element("span", {}, [])])` is rendered inside a `<div>`
- **THEN** the `<p>` and `<span>` SHALL be rendered as direct children of the `<div>`
- **AND** no wrapper DOM node SHALL be created

#### Scenario: Fragment with single child
- **WHEN** a `FragmentElement` contains exactly one child
- **THEN** that child SHALL be rendered normally in the parent

#### Scenario: Fragment with zero children
- **WHEN** a `FragmentElement` contains no children
- **THEN** nothing SHALL be rendered (no DOM nodes created)

#### Scenario: Fragment with zero children during hydration
- **WHEN** a `FragmentElement` contains no children and the page is being hydrated
- **THEN** `_hydrate_node()` SHALL return without creating any DOM nodes
- **AND** no error SHALL be raised

#### Scenario: Fragment children hydrate via DynamicElement._hydrate_node
- **WHEN** a `FragmentElement` with children is hydrated
- **THEN** each child SHALL be hydrated via the standard `DynamicElement._hydrate_node()` path
- **AND** unmounted children SHALL be scheduled via `AsyncSchedulerPort`

### Requirement: Template engine shall support conditional rendering via {% if %} blocks

`{% if var %}`, `{% elif var %}`, `{% else %}`, `{% endif %}` SHALL provide conditional rendering. Signal conditions SHALL use `switch()` for reactive updates. Non-Signal conditions SHALL be evaluated at bind time.

#### Scenario: Reactive if with Signal condition
- **WHEN** `{% if show %}...{% endif %}` is used and `show` is a `Signal` in the context
- **THEN** `switch()` SHALL be generated with the Signal as the case condition
- **AND** the branch content SHALL update reactively when the Signal changes

#### Scenario: Static if with plain bool
- **WHEN** `{% if flag %}...{% endif %}` is used and `flag` is `True` (plain bool)
- **THEN** the branch content SHALL be included in the Element tree
- **AND** no `switch()` SHALL be generated (non-reactive)

#### Scenario: Static if with falsy value
- **WHEN** `{% if flag %}...{% endif %}` is used and `flag` is `False`
- **THEN** no children SHALL be produced for that branch

#### Scenario: If-elif-else chain
- **WHEN** `{% if a %}A{% elif b %}B{% else %}C{% endif %}` is used
- **THEN** the first truthy branch SHALL be rendered
- **AND** if no branch is truthy, the `{% else %}` branch SHALL be rendered

#### Scenario: Multiple elements in branch
- **WHEN** an `{% if %}` branch contains multiple HTML elements
- **THEN** the elements SHALL be wrapped in a `FragmentElement` for the `switch()` generator

#### Scenario: Dot notation in condition
- **WHEN** `{% if item.visible %}` is used
- **THEN** `resolve_var("item.visible", ctx)` SHALL be called to evaluate the condition

#### Scenario: Mixed Signal and static conditions in if-elif chain
- **WHEN** an if-elif chain contains both Signal and plain value conditions (e.g., `{% if signal_a %}A{% elif plain_bool %}B{% endif %}`)
- **THEN** the reactive path (`switch()`) SHALL be used
- **AND** `SwitchCasesSignal` (`_switch.py:23`) SHALL be widened from `list[tuple[SignalBase[Any], NodeGenerator]]` to `list[tuple[Any, NodeGenerator]]` so that mixed-type conditions can be passed to `SwitchElement.__init__` without a cast
- **AND** plain value conditions SHALL be evaluated with `truth()` at evaluation time (not wrapped in a Signal)

#### Scenario: Malformed if block (missing endif)
- **WHEN** `{% if x %}...` has no matching `{% endif %}`
- **THEN** a `WebComPyException` SHALL be raised

### Requirement: Template engine shall support list iteration via {% for %} blocks

`{% for item in items %}`, `{% endfor %}` SHALL provide iteration. `ReactiveList`/`ReactiveDict` iterables SHALL use `repeat()` for reactive updates. Plain `list`/`dict` SHALL use list comprehension.

#### Scenario: Reactive for with ReactiveList
- **WHEN** `{% for item in items %}...{% endfor %}` is used and `items` is a `ReactiveList`
- **THEN** `repeat()` SHALL be generated with the ReactiveList
- **AND** the list content SHALL update reactively when items are added/removed

#### Scenario: Reactive for with ReactiveDict
- **WHEN** `{% for value in my_dict %}...{% endfor %}` is used and `my_dict` is a `ReactiveDict`
- **THEN** `repeat()` SHALL be generated with the ReactiveDict

#### Scenario: Static for with plain list
- **WHEN** `{% for item in plain_list %}...{% endfor %}` is used and `plain_list` is a `list`
- **THEN** children SHALL be generated via list comprehension (non-reactive)
- **AND** no `repeat()` SHALL be used

#### Scenario: Multiple elements per iteration (reactive)
- **WHEN** the `{% for %}` body contains multiple elements and the iterable is reactive
- **THEN** each iteration's children SHALL be wrapped in a `FragmentElement` within the `repeat()` template

#### Scenario: Multiple elements per iteration (static)
- **WHEN** the `{% for %}` body contains multiple elements and the iterable is static
- **THEN** all elements SHALL be appended directly to the parent's children list

#### Scenario: Loop variable available in body
- **WHEN** `{% for item in items %}<p>{{ item.name }}</p>{% endfor %}` is used
- **THEN** `item` SHALL be added to the binding context for the body
- **AND** `{{ item.name }}` SHALL resolve within the loop body

#### Scenario: Dot notation in iterable reference
- **WHEN** `{% for post in user.posts %}` is used
- **THEN** `resolve_var("user.posts", ctx)` SHALL resolve the iterable

#### Scenario: Nested control flow
- **WHEN** `{% for item in items %}{% if item.visible %}<li>{{ item.name }}</li>{% endif %}{% endfor %}` is used
- **THEN** the `{% if %}` SHALL be correctly nested inside the `{% for %}` body and evaluated per iteration

#### Scenario: Malformed for block (missing endfor)
- **WHEN** `{% for item in items %}...` has no matching `{% endfor %}`
- **THEN** a `WebComPyException` SHALL be raised

#### Scenario: Dict key-value unpacking
- **WHEN** `{% for key, value in my_dict %}<p>{{ key }}: {{ value }}</p>{% endfor %}` is used with `my_dict` being a `ReactiveDict`
- **THEN** `repeat()` SHALL be generated using the `Callable[[V, K], ElementChildren]` overload
- **AND** both `key` and `value` SHALL be available as loop variables in the body context
- **AND** the body SHALL update reactively when dict entries change

### Requirement: CSS text shall be parsed into scoped style dict structure

The framework SHALL provide a `css_text(source: str) -> dict[str, StyleDict]` function that parses CSS text strings into the existing `StyleDict` (nested dict) format. The parser SHALL handle all CSS constructs supported by WebComPy's scoped_style system, including selectors, combinator selectors, pseudo-classes/elements, at-rules (`@media`, `@supports`, `@container`, `@keyframes`), and nested rules. `textwrap.dedent` SHALL be applied to the source before parsing. The return type `dict[str, StyleDict]` matches the `scoped_style` setter type (`_generator.py:253`).

#### Scenario: Basic selectors and properties
- **WHEN** `css_text(".btn { color: red; }")` is called
- **THEN** it SHALL return `{".btn": {"color": "red"}}`

#### Scenario: Pseudo-class nesting
- **WHEN** `css_text(".btn:hover { background: blue; }")` is called
- **THEN** it SHALL return `{".btn:hover": {"background": "blue"}}`

#### Scenario: Nested pseudo-class (implicit nesting)
- **WHEN** `css_text(".btn { color: red; :hover { background: blue; } }")` is called
- **THEN** it SHALL return `{".btn": {"color": "red", ":hover": {"background": "blue"}}}`

#### Scenario: At-rule
- **WHEN** `css_text("@media (max-width: 768px) { .btn { font-size: 12px; } }")` is called
- **THEN** it SHALL return `{"@media (max-width: 768px)": {".btn": {"font-size": "12px"}}}`

#### Scenario: @keyframes
- **WHEN** `css_text("@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }")` is called
- **THEN** it SHALL return `{"@keyframes spin": {"0%": {"transform": "rotate(0deg)"}, "100%": {"transform": "rotate(360deg)"}}}`

#### Scenario: Nested at-rules
- **WHEN** `css_text("@media (max-width: 768px) { @supports (display: grid) { .btn { display: grid; } } }")` is called
- **THEN** nested at-rules SHALL be parsed into nested dict structure

#### Scenario: Combinator selectors
- **WHEN** `css_text(".a > .b { color: red; }")` is called
- **THEN** it SHALL return `{".a > .b": {"color": "red"}}`

#### Scenario: CSS comments stripped
- **WHEN** `css_text("/* comment */ .btn { color: red; }")` is called
- **THEN** comments SHALL be stripped and the result SHALL be `{".btn": {"color": "red"}}`

#### Scenario: At-rule with paren-contained colon
- **WHEN** `@media (max-width: 768px)` contains `:` inside parentheses
- **THEN** the parser SHALL NOT treat the internal `:` as a property separator

#### Scenario: File-based CSS via load_text composition
- **WHEN** a developer writes `css_text(await load_text("styles/button.css"))` inside an async component setup
- **THEN** `load_text` SHALL read the file content (via `ResourcePort`) and `css_text` SHALL parse the returned string
- **AND** on the server, the read SHALL be recorded by `ServerResourcePort` for hydration payload embedding
- **AND** on the browser, the same `load_text` call SHALL resolve from the hydration payload (no fetch needed if the resource was read during SSR)

### Requirement: CSS text templates shall support {{ }} variable interpolation

The framework SHALL provide a `css_text_template(source: str, context: dict) -> Callable[[], dict[str, StyleDict]]` function. The returned factory SHALL resolve `{{ varname }}` holes from the context using `resolve_holes` (from `_holes.py`), parse the resolved CSS text to `dict[str, StyleDict]`, and be suitable for use with `reactive_scoped_style`. `ReactiveScopedStyleFunc` (`_reactive_scoped_style.py:61`) SHALL be corrected from `Callable[[], StyleDict]` to `Callable[[], dict[str, StyleDict]]` so that `css_text_template`'s return type is directly assignable. This aligns the alias with the runtime contract of `render_css()` / `_apply_scope()` which iterate `.items()` over the factory return value (selector-keyed top-level dict).

#### Scenario: Factory resolves {{ }} before parsing
- **WHEN** `css_text_template(".btn { color: {{ color }}; }", {"color": Signal("blue")})` returns a factory
- **AND** the factory is called
- **THEN** `{{ color }}` SHALL be resolved to `"blue"` by reading `color.value`
- **AND** the result SHALL be `{".btn": {"color": "blue"}}`

#### Scenario: Signal dependency tracking in factory
- **WHEN** the returned factory is wrapped in `reactive_scoped_style` (creating a `Computed`)
- **AND** a referenced Signal changes
- **THEN** the `Computed` SHALL re-evaluate the factory, re-resolve `{{ }}`, and re-parse CSS
- **AND** the `<style>` element SHALL update reactively

### Requirement: css_text and css_text_template shall be exported from webcompy.template

Both `css_text` and `css_text_template` SHALL be importable from `webcompy.template`.

#### Scenario: Import
- **WHEN** a developer writes `from webcompy.template import css_text, css_text_template`
- **THEN** both functions SHALL be available

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

#### Scenario: File-based Markdown via load_text composition
- **WHEN** a developer writes `render_markdown(await load_text("page.md"), ctx)` inside an async component setup
- **THEN** `load_text` SHALL read the file content and `render_markdown` SHALL parse the returned string
- **AND** on the server, the read SHALL be recorded for hydration; on the browser, the same call SHALL resolve from the payload

### Requirement: {% %} directives shall not be wrapped in paragraph tags

Line-by-line `{% %}` directives (e.g., `{% for item in items %}`) that would be wrapped in `<p>` tags by the Markdown parser SHALL have those `<p>` wrappers removed before passing to `render_template`.

#### Scenario: {% for %} directive unwrapped
- **WHEN** Markdown processing produces `<p>{% for item in items %}</p>`
- **THEN** the `<p>` wrapper SHALL be stripped to `{% for item in items %}`

#### Scenario: {% if %} with text preserved
- **WHEN** Markdown produces `<p>{% if x %}visible text{% endif %}</p>`
- **THEN** the `<p>` SHALL NOT be stripped (directive has sibling text content)

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
