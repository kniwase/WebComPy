## ADDED Requirements

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

Tags not in the HtmlTags literal SHALL be treated as regular HTML elements. No error SHALL be raised for unknown tag names.

#### Scenario: Unknown tag
- **WHEN** the template contains `<widget>text</widget>` and "widget" is not in HtmlTags
- **THEN** `Element("widget", {}, [TextElement("text")])` SHALL be created
