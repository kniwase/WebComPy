# Template Engine

## Purpose

WebComPy provides an HTML template engine that parses template strings into reactive WebComPy Element trees using the stdlib `html.parser.HTMLParser`. This enables developers to define component UIs with familiar HTML syntax and `{{ varname }}` interpolation instead of the verbose Python element API (`html.DIV({...}, ...)`), while preserving the framework's reactive model — Signal references in text and attribute positions flow into the existing `TextElement` and `Computed`-valued attribute pipelines unchanged.

The template engine is the foundation for a family of related capabilities (control flow, component tags, file loading, CSS text, markdown) that reuse its parser, binder, and shared `_holes.py` interpolation utilities.

The template engine is syntactic sugar over WebComPy's Element/Component system: Jinja2-inspired but explicitly NOT Jinja2-compatible. Composition is done via components and slots, so template inheritance (`extends`/`block`/`macro`/`include`) is a permanent non-goal — unsupported Jinja2 directives are rejected at compile time rather than emulated.

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

Boolean HTML attributes (e.g., `disabled`, `checked`) that have no value SHALL be converted to `True` for the attribute dict. An attribute with an explicit empty-string value (`alt=""`) is NOT boolean and SHALL be preserved as the empty string `""`.

#### Scenario: Boolean attribute conversion
- **WHEN** the template contains `<input disabled>`
- **THEN** the attribute SHALL be `{"disabled": True}` (which `_proc_attr` converts to `""` in the DOM)

#### Scenario: Boolean attribute with explicit value
- **WHEN** the template contains `<input disabled="disabled">`
- **THEN** the attribute SHALL be `{"disabled": "disabled"}` (string value preserved)

#### Scenario: Empty-string attribute value is not boolean
- **WHEN** the template contains `<img alt="">`
- **THEN** the attribute SHALL be `{"alt": ""}` (empty string, not `True`)

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

`{{ varname }}` and `{{ a.b.c }}` (dot notation) SHALL interpolate variables from the context into text content. Single-segment plain paths that resolve to a Signal SHALL pass the Signal directly to `TextElement` for reactive updates. Multi-segment plain paths where an intermediate segment resolves to a Signal SHALL unwrap the Signal (read `.value`) and continue resolution, wrapping the result in an implicit `Computed` so downstream text updates reactively when the intermediate Signal changes. `{{ }}` holes SHALL additionally accept the safe expression subset (per the expression-language requirement), with Signal-referencing expressions wrapped in an implicit `Computed`.

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

#### Scenario: Dotted path with intermediate Signal
- **WHEN** `{{ user.profile.name }}` is used where `user.profile` resolves to a `Signal({"name": "Alice"})`
- **THEN** the intermediate Signal SHALL be unwrapped (`.value` read) and the remaining segment `name` SHALL resolve to `"Alice"`

#### Scenario: Reactive dotted path with intermediate Signal
- **WHEN** `{{ user.profile.name }}` has an intermediate `Signal` at the `.profile` position and that Signal is updated
- **THEN** the rendered text SHALL update reactively via an implicit `Computed` that re-resolves the remaining segments through the unwrapped Signal

#### Scenario: Expression in text content
- **WHEN** `render_template("<p>{{ price * quantity }}</p>", {"price": 100, "quantity": 3})` is called
- **THEN** the text content SHALL be `"300"`

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

`{{ }}` in attribute values SHALL accept the safe expression subset. Attribute interpolation SHALL produce reactive `Computed` signals when any referenced variable is a `SignalBase` (including Signals referenced inside expressions). When no Signal is referenced, static string evaluation SHALL be used.

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

#### Scenario: Expression with Signal in attribute
- **WHEN** `style="width: {{ ratio * 100 }}%"` is used with `ratio` being `Signal(0.5)`
- **THEN** a `Computed` SHALL be generated evaluating to `"width: 50%"` (via `format_value` rules)
- **AND** the attribute SHALL update when `ratio` changes

### Requirement: Template expression language shall evaluate a safe Python expression subset

`{{ }}` holes SHALL accept expressions parsed via `ast.parse(source, mode="eval")` at template compile time and validated against a whitelist of node types: `BinOp`, `BoolOp`, `UnaryOp`, `Compare` (including `in`/`not in`/`is`/`is not`), `IfExp`, `Subscript`, `Attribute`, `Call`, `List`, `Tuple`, `Dict`, `Set`, `Name`, and `Constant`. Comprehensions, lambdas, assignment expressions, and any node type outside the whitelist SHALL be rejected with `WebComPyException` at compile time. Call targets SHALL be restricted to `Name` or `Attribute` nodes, and no attribute segment anywhere in an expression SHALL begin with `_`.

Hole extraction SHALL use a depth-aware scanner that tracks `{`/`}` nesting depth and skips braces inside string literals, so nested dict/set literals (e.g., `{{ {'a': {'b': 2}} }}`) are extracted as a single hole.

#### Scenario: Arithmetic expression
- **WHEN** `render_template("<p>{{ count + 1 }}</p>", {"count": 5})` is called
- **THEN** the text content SHALL be `"6"`

#### Scenario: Subscript expression
- **WHEN** `render_template("<p>{{ items[0] }}</p>", {"items": ["a", "b"]})` is called
- **THEN** the text content SHALL be `"a"`

#### Scenario: Method call expression
- **WHEN** `render_template("<p>{{ name.upper() }}</p>", {"name": "alice"})` is called
- **THEN** the text content SHALL be `"alice".upper()` → `"ALICE"`

#### Scenario: Nested dict literal extracted correctly
- **WHEN** the template contains `{{ {'a': {'b': 2}}['a']['b'] }}`
- **THEN** the hole SHALL be extracted as one expression and evaluate to `2`

#### Scenario: Whitelist rejection
- **WHEN** the template contains `{{ [x for x in items] }}` or `{{ (lambda: 1)() }}`
- **THEN** `WebComPyException` SHALL be raised at compile time naming the unsupported construct

#### Scenario: Dunder access rejected
- **WHEN** the template contains `{{ x.__class__ }}` or `{{ x._secret() }}`
- **THEN** `WebComPyException` SHALL be raised at compile time

#### Scenario: Expression syntax error at compile time
- **WHEN** the template contains `{{ count + }}`
- **THEN** `WebComPyException` SHALL be raised at compile time with the parse error detail

### Requirement: Template expressions shall support Jinja2-style filters

A `BinOp(BitOr)` node whose right operand is a `Name` registered in the built-in filter registry, or a `Call` whose func is such a `Name`, SHALL be reinterpreted as a filter application, with the left operand as the first filter argument and any call arguments appended. A `BitOr` whose right operand does not match a registered filter SHALL evaluate as a plain Python bitwise-or. Filter registry names SHALL take precedence over context variables on the right of `|`. The built-in registry SHALL provide at minimum: `upper`, `lower`, `title`, `capitalize`, `trim`, `length`, `join`, `default`, `replace`, `round`, `int`, `float`, `string`, `first`, `last`, `abs`. Filter chaining (`a | b | c`) SHALL work via left-associativity. The registry SHALL be internal; no user-registration API is provided.

#### Scenario: Simple filter
- **WHEN** `render_template("<p>{{ name | upper }}</p>", {"name": "alice"})` is called
- **THEN** the text content SHALL be `"ALICE"`

#### Scenario: Filter with arguments
- **WHEN** `render_template("<p>{{ items | join(', ') }}</p>", {"items": ["a", "b"]})` is called
- **THEN** the text content SHALL be `"a, b"`

#### Scenario: Filter chain
- **WHEN** `{{ name | trim | upper }}` is used with `name` being `"  alice  "`
- **THEN** the result SHALL be `"ALICE"`

#### Scenario: Non-filter BitOr falls back to bitwise-or
- **WHEN** `{{ flags | mask }}` is used with `flags` being `0b1100`, `mask` being `0b1010`, and `mask` not a registered filter
- **THEN** the result SHALL be `0b1110` (14)

#### Scenario: Filter registry precedence over context variable
- **WHEN** `{{ name | upper }}` is used and the context also contains a variable named `upper`
- **THEN** the registered `upper` filter SHALL be applied (registry wins)

### Requirement: Signal-referencing expressions shall re-evaluate reactively via implicit Computed

Each hole, condition, or iterable target SHALL be classified at bind time. A **plain path** (only `Name`/`Attribute` chain) whose final resolved value is a Signal SHALL pass the Signal through unwrapped (single-segment paths like `{{ count }}`); a plain path where an intermediate segment resolves to a Signal SHALL wrap the remaining resolution in an implicit `Computed` that unwraps the intermediate Signal and re-resolves on change. A **true expression** (any other form) whose referenced context values include a `SignalBase` SHALL be wrapped in a `Computed` closure that re-evaluates the expression; a true expression without Signal references SHALL be evaluated once. During expression evaluation, encountering a `SignalBase` SHALL read `.value` (unwrap), registering the dependency via the active-consumer mechanism. Unwrapping a `ReactiveList`/`ReactiveDict` yields the raw collection (coarse dependency).

#### Scenario: Reactive arithmetic
- **WHEN** `render_template("<p>{{ count + 1 }}</p>", {"count": Signal(5)})` is called
- **THEN** a `Computed` SHALL back the text node
- **AND** setting `count.value = 10` SHALL update the rendered text to `"11"`

#### Scenario: Non-Signal expression evaluates once
- **WHEN** `render_template("<p>{{ a + b }}</p>", {"a": 1, "b": 2})` is called
- **THEN** the text SHALL be the static `"3"` with no `Computed` created

#### Scenario: Plain path keeps pass-through behavior
- **WHEN** `render_template("<p>{{ count }}</p>", {"count": Signal(5)})` is called
- **THEN** `TextElement(Signal(5))` SHALL be created directly (Signal passed through, not wrapped in `Computed`)

#### Scenario: Signal mid-expression unwrapped
- **WHEN** `{{ user.name + '!' }}` is used with `user.name` resolving to a `Signal`
- **THEN** evaluation SHALL read `.value` and the expression SHALL re-evaluate when that Signal changes

#### Scenario: Intermediate Signal in dotted path unwrapped
- **WHEN** `{{ user.profile.name }}` is used and `user.profile` resolves to a `Signal`
- **THEN** `resolve_var` SHALL return a `Computed` that unwraps the intermediate Signal and resolves the remaining segments
- **AND** the rendered text SHALL update when the intermediate Signal changes

### Requirement: Template engine shall support {# #} comments

`{# ... #}` spans SHALL be stripped from the template source before parsing, in both `render_template` and `render_markdown` paths, and SHALL NOT produce any node. Comments inside `{% raw %}` blocks SHALL be preserved as literal text.

#### Scenario: Comment stripped
- **WHEN** the template contains `<p>Hello {# this is a comment #} World</p>`
- **THEN** the rendered text SHALL be `"Hello  World"` with no node for the comment

#### Scenario: Comment spanning template syntax
- **WHEN** the template contains `{# {{ x }} {% if y %} #}<p>ok</p>`
- **THEN** the entire comment SHALL be removed and only `<p>ok</p>` SHALL render

#### Scenario: Comment inside raw block preserved
- **WHEN** the template contains `{% raw %}{# not a comment #}{% endraw %}`
- **THEN** the literal text `{# not a comment #}` SHALL be rendered

### Requirement: Template engine shall support {% raw %} blocks for literal output

`{% raw %}...{% endraw %}` SHALL emit their content without `{{ }}`, `{% %}`, or `{# #}` processing. Tags inside raw blocks SHALL still parse as HTML elements; only template-syntax processing is disabled. An unclosed `{% raw %}` SHALL raise `WebComPyException` at compile time.

#### Scenario: Literal double-brace output
- **WHEN** the template contains `<p>{% raw %}{{ not_a_var }}{% endraw %}</p>`
- **THEN** the rendered text SHALL be the literal `{{ not_a_var }}` with no context lookup

#### Scenario: Literal directive output
- **WHEN** the template contains `{% raw %}{% if x %}{% endraw %}`
- **THEN** the literal text `{% if x %}` SHALL be rendered and no conditional SHALL be executed

#### Scenario: Tags inside raw still parse
- **WHEN** the template contains `{% raw %}<b>{{ x }}</b>{% endraw %}`
- **THEN** a `<b>` element SHALL be created whose text is the literal `{{ x }}`

#### Scenario: Unclosed raw block
- **WHEN** the template contains `{% raw %}{{ x }}` with no `{% endraw %}`
- **THEN** `WebComPyException` SHALL be raised at compile time

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

`{% if expr %}`, `{% elif expr %}`, `{% else %}`, `{% endif %}` SHALL provide conditional rendering. Conditions SHALL accept the safe expression subset in addition to dotted paths. Conditions resolving to (or Computed-wrapping) a `SignalBase` SHALL use `switch()` for reactive updates. Non-Signal conditions SHALL be evaluated at bind time.

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

#### Scenario: Expression condition with Signal
- **WHEN** `{% if count > 3 %}big{% endif %}` is used with `count` being `Signal(5)`
- **THEN** a `Computed` evaluating `count.value > 3` SHALL be used as the reactive case condition
- **AND** the branch SHALL toggle when `count` crosses the threshold

#### Scenario: Expression condition without Signal
- **WHEN** `{% if items | length > 0 %}...{% endif %}` is used with `items` being a plain list
- **THEN** the condition SHALL be evaluated once at bind time (non-reactive)

#### Scenario: Mixed Signal and static conditions in if-elif chain
- **WHEN** an if-elif chain contains both Signal and plain value conditions (e.g., `{% if signal_a %}A{% elif plain_bool %}B{% endif %}`)
- **THEN** the reactive path (`switch()`) SHALL be used
- **AND** `SwitchCasesSignal` (`_switch.py:23`) SHALL be widened from `list[tuple[SignalBase[Any], NodeGenerator]]` to `list[tuple[Any, NodeGenerator]]` so that mixed-type conditions can be passed to `SwitchElement.__init__` without a cast
- **AND** plain value conditions SHALL be evaluated with `truth()` at evaluation time (not wrapped in a Signal)

#### Scenario: Malformed if block (missing endif)
- **WHEN** `{% if x %}...` has no matching `{% endif %}`
- **THEN** a `WebComPyException` SHALL be raised

### Requirement: Template engine shall support list iteration via {% for %} blocks

`{% for item in iterable %}`, `{% endfor %}` SHALL provide iteration; the iterable target SHALL accept the safe expression subset in addition to dotted paths. `ReactiveList`/`ReactiveDict` iterables SHALL use `repeat()` for reactive updates. Expression iterables referencing Signals SHALL be wrapped in `Computed` and passed to `repeat()`. Plain `list`/`dict` SHALL use list comprehension.

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

#### Scenario: Expression iterable with Signal
- **WHEN** `{% for item in items[:3] %}...{% endfor %}` is used with `items` being a `ReactiveList`
- **THEN** the slice expression SHALL be wrapped in a `Computed` and passed to `repeat()`
- **AND** the rendered rows SHALL update when `items` changes

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

#### Scenario: ReactiveDict value that is an Element rendered as child
- **WHEN** `{% for v in d %}{{ v }}{% endfor %}` is used with a `ReactiveDict` whose values include `Element` or `Component` instances
- **THEN** each Element/Component SHALL be placed as a direct child element (not stringified)
- **AND** scalar values SHALL continue to render as text with reactive updates

#### Scenario: ReactiveDict loop value keeps fresh value semantics
- **WHEN** a `ReactiveDict` key is updated with a new value (including a nested `Signal` value) while a loop over the dict is rendered
- **THEN** the loop body SHALL observe the current stored value (not a stale callback argument), unwrapping nested `Signal` values
- **AND** the rendered content SHALL update reactively

### Requirement: `{% for %}` loops shall expose loop metadata

Inside a `{% for %}` body, a `loop` metadata object SHALL be available with the attributes `loop.index` (1-based position), `loop.index0` (0-based position), `loop.revindex` (1-based position from the end), `loop.revindex0` (0-based position from the end), `loop.first` (true on the first iteration), `loop.last` (true on the last iteration), and `loop.length` (total iteration count). Metadata SHALL always reflect the item's current position:

- In static loops (plain `list`/`dict`), metadata values SHALL be exact at expansion time.
- In `ReactiveList` loops (unkeyed, full-rebuild semantics), metadata values SHALL be exact after every refresh.
- In `ReactiveDict` loops (key-based reconciliation reuses child DOM across add/remove/reorder), metadata SHALL update reactively so that reused children observe correct positions, lengths, and first/last flags after any mutation.

Metadata SHALL be available in HTML template loops (`render_template` and markdown text paths) and in markdown list-body for-loops (`MarkdownForElement`).

#### Scenario: Static loop metadata
- **WHEN** `render_template("<ul>{% for x in items %}<li>{{ loop.index }}: {{ x }}</li>{% endfor %}</ul>", {"items": ["a", "b"]})` is called
- **THEN** the rendered items SHALL be `<li>1: a</li>` and `<li>2: b</li>`

#### Scenario: First and last flags
- **WHEN** a `{% for %}` body uses `{{ loop.first }}` and `{{ loop.last }}` over a 3-item list
- **THEN** `loop.first` SHALL be true only for the first item and `loop.last` SHALL be true only for the last item

#### Scenario: ReactiveDict metadata updates on reorder
- **WHEN** a `{% for v in d %}` loop over a `ReactiveDict` renders `{{ loop.index }}` for each item
- **AND** the dict is mutated so that key order changes (or keys are added/removed)
- **THEN** reused children SHALL display updated positions, lengths, and first/last flags without being re-created

#### Scenario: ReactiveList metadata after mutation
- **WHEN** a `{% for item in items %}` loop over a `ReactiveList` renders `{{ loop.index }}`
- **AND** an item is appended
- **THEN** the rebuilt children SHALL show exact 1-based positions and an updated `loop.length`

#### Scenario: Metadata in markdown list-body for-loops
- **WHEN** a markdown `{% for item in items %}` list-body block references `{{ loop.index }}`
- **THEN** each iteration SHALL render its 1-based position

### Requirement: Loop metadata shadowing shall follow innermost-wins semantics

In nested `{% for %}` loops, the inner loop's `loop` SHALL shadow the outer loop's `loop` within the inner body. A user-declared loop variable named `loop` SHALL shadow the metadata object within that loop body. Outside any `{% for %}`, a context variable named `loop` SHALL be unaffected.

#### Scenario: Nested loops
- **WHEN** nested `{% for %}` loops both reference `{{ loop.index }}`
- **THEN** the reference inside the inner loop body SHALL resolve to the inner loop's position

#### Scenario: User loop variable named loop
- **WHEN** a template uses `{% for loop in items %}{{ loop }}{% endfor %}`
- **THEN** `loop` SHALL resolve to each item (the loop variable shadows the metadata)

### Requirement: Template engine shall reject unsupported Jinja2 directives

Directive spans whose name is a recognized Jinja2 tag that WebComPy does not support — `extends`, `block`/`endblock`, `macro`/`endmacro`, `call`/`endcall`, `include`, `import`, `from`, `set`, `with`/`endwith`, `filter`/`endfilter`, `do`, `trans`/`endtrans`, `pluralize`, `autoescape`/`endautoescape`, `debug` — SHALL raise `WebComPyException` at compile time. The message SHALL concisely state that the directive is not supported; no design rationale is required in the message. This applies to both `render_template` and the markdown rendering path.

#### Scenario: extends rejected
- **WHEN** a template contains `{% extends "base.html" %}`
- **THEN** `WebComPyException` SHALL be raised at compile time with a message stating `{% extends %}` is not supported

#### Scenario: block rejected in markdown
- **WHEN** markdown source contains `{% block content %}`
- **THEN** `WebComPyException` SHALL be raised stating the directive is not supported

### Requirement: Template engine shall reject unknown directives

A `{% word %}` span whose name matches neither the supported directives (`if`, `elif`, `else`, `endif`, `for`, `endfor`) nor the known-unsupported list SHALL raise `WebComPyException` at compile time with a concise "unknown directive" message. Literal `{%` output SHALL remain available via `{% raw %}`. Directive rejection applies to text content; `{%` inside attribute values SHALL remain literal.

#### Scenario: Typo rejected
- **WHEN** a template contains `{% endfo %}`
- **THEN** `WebComPyException` SHALL be raised at compile time identifying the unknown directive

#### Scenario: Literal percent-brace via raw
- **WHEN** a template contains `{% raw %}{% anything %}{% endraw %}`
- **THEN** the content SHALL render literally without error

#### Scenario: Directive-like span in attribute stays literal
- **WHEN** a template contains `<div title="{% extends %}">`
- **THEN** no directive error SHALL be raised and the attribute value SHALL remain literal

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

`DefaultMarkdownParser.render(source)` SHALL convert Markdown text to HTML strings using a two-phase CommonMark parser (block structure per the container-stack algorithm; inline content per the delimiter-run algorithm), extended with the GFM extensions (tables, task list items, strikethrough, autolinks, disallowed raw HTML). `textwrap.dedent` SHALL be applied to multi-line sources at the framework layer (`render_markdown`) only; the parser itself SHALL NOT dedent. Tabs SHALL be handled per CommonMark (advance to the next 4-column stop, with partial-tab support); no global tab-to-spaces normalization SHALL be performed.

Inline parsing SHALL be implemented as a character-scanning tokenizer followed by delimiter-stack processing (not sequential regex substitution), and SHALL be linear-time for adversarial inputs.

#### Scenario: ATX headings

- **WHEN** source contains `# Title` through `###### Sub`
- **THEN** the output SHALL be `<h1>Title</h1>` through `<h6>Sub</h6>`
- **AND** closing hash sequences preceded by a space (`## Title ##`) SHALL be stripped
- **AND** `#hashtag` (no space after `#`) SHALL NOT be a heading (CommonMark requires a space)

#### Scenario: Setext headings

- **WHEN** source contains `Title` followed by an underline of `=` characters
- **THEN** the output SHALL be `<h1>Title</h1>`
- **AND** an underline of `-` characters SHALL produce `<h2>Title</h2>` (not a thematic break)

#### Scenario: Paragraphs and line breaks
- **WHEN** source contains consecutive non-blank lines
- **THEN** they SHALL be joined into `<p>text</p>` with soft breaks preserved as newlines per spec
- **AND** a line ending in two or more spaces or a backslash SHALL produce `<br>` (hard break)

#### Scenario: Fenced code blocks

- **WHEN** source contains lines between ``` or `~~~` fences (3+ characters, up to 3 spaces indent)
- **THEN** the output SHALL be `<pre><code>content</code></pre>`
- **AND** the fence info string's first word (entity-decoded) SHALL be emitted as `<code class="language-{word}">` when present
- **AND** the closing fence SHALL be at least as long as the opening fence and of the same character

#### Scenario: Indented code blocks

- **WHEN** source contains lines indented by 4+ columns outside a list context
- **THEN** they SHALL be emitted as `<pre><code>` blocks per CommonMark indented-code rules (including blank-line handling and interruption rules)

#### Scenario: Lists

- **WHEN** source contains `-`/`+`/`*` bullet items or `1.`/`1)` ordered items
- **THEN** the output SHALL follow CommonMark list rules (marker consistency, `<ol start="N">` when N != 1, loose vs tight rendering, block children inside items)
- **AND** tabs SHALL be normalized per column rules for indent calculation (never a fixed 2-space rule)

#### Scenario: Nested and mixed container structures

- **WHEN** source contains nested blockquotes (`> > inner`), blockquotes containing lists/headings/code, lazy continuation lines, or lists containing fenced code/headings/blockquotes
- **THEN** the container stack SHALL produce the CommonMark-specified nesting
- **AND** lazy continuation lines SHALL attach to the open paragraph per spec

#### Scenario: Thematic breaks

- **WHEN** source contains `---`, `***`, `___`, or spaced variants (`* * *`, `- - -`) on their own line (0-3 spaces indent)
- **THEN** the output SHALL be `<hr>`
- **AND** a `-`-based line directly under a paragraph line SHALL be a setext underline instead

#### Scenario: HTML blocks

- **WHEN** source contains any of the seven CommonMark HTML block types (including multi-line comments, processing instructions, declarations, and CDATA)
- **THEN** they SHALL be preserved as-is through their spec-defined end condition
- **AND** component tags (`<user-card>`) SHALL continue to pass through unchanged

#### Scenario: Link reference definitions absorbed

- **WHEN** source contains link reference definitions (`[label]: destination "title"`)
- **THEN** they SHALL produce no HTML output
- **AND** the definitions SHALL be retained on the parse result for inline resolution

#### Scenario: GFM tables

- **WHEN** source contains a header row, a valid delimiter row (`| --- | :-: | ---: |`), and zero or more body rows
- **THEN** the output SHALL be `<table><thead><tr><th>...` per GFM, with column alignment reflected per GFM output conventions and cell contents inline-rendered
- **AND** rows with mismatched cell counts SHALL be handled per GFM (excess dropped, missing filled empty)

#### Scenario: GFM task list items

- **WHEN** a list item begins with `[ ]`, `[x]`, or `[X]` followed by whitespace
- **THEN** the item SHALL begin with `<input type="checkbox" disabled="">` (plus `checked=""` when checked) per GFM
- **AND** the checkbox SHALL be static HTML with no reactive binding

#### Scenario: Emphasis and strong via delimiter runs
- **WHEN** source contains `*`/`_` delimiters in any spec-valid configuration
- **THEN** `<em>`/`<strong>` SHALL be produced per the CommonMark delimiter algorithm, including `***bold-italic***`, nested forms (`*a **b** c*`), and intraword underscore rules (`foo_bar_baz` remains literal; `_em_` and `__strong__` are active)
- **NOTE**: Symmetric delimiter runs of length ≥4 (e.g. `****foo****`) produce nested `<strong>` levels matching commonmark.js/py and markdown-it behavior, rather than collapsing to a single level (as cmark-gfm does). This is a documented ecosystem-wide divergence: the portable reference implementations (commonmark.js, commonmark.py) share the same nested behavior; only the C cmark-gfm collapses. The WebComPy parser matches the broader ecosystem. See `openspec/changes/refactor-markdown-inline-parser/specs/markdown-conformance/spec.md` for the deviation catalog.

#### Scenario: GFM strikethrough
- **WHEN** source contains `~` or `~~` delimiters per the GFM extension
- **THEN** `<del>` SHALL be produced per the delimiter algorithm

#### Scenario: Code spans
- **WHEN** source contains backtick strings of any length (`` `a` ``, `` ``a`b`` ``)
- **THEN** matching variable-length code spans SHALL be produced per spec
- **AND** content SHALL be HTML-escaped but otherwise literal (no emphasis, entities, or template processing inside)

#### Scenario: Backslash escapes and entities
- **WHEN** source contains backslash-escaped punctuation (`\*`) or entity/numeric references (`&copy;`, `&#65;`, `&#x41;`)
- **THEN** escapes SHALL yield the literal punctuation character and references SHALL resolve per spec (via stdlib `html.entities`), except inside code spans/blocks where both remain literal

#### Scenario: Links and images
- **WHEN** source contains inline links/images with balanced-paren or `<...>` destinations and optional titles (`"..."`, `'...'`, `(...)`), or full/collapsed/shortcut reference links
- **THEN** `<a href>`/`<img src>` SHALL be produced per spec, with titles and reference resolution via the block-layer definition table (CommonMark label normalization)

#### Scenario: Autolinks and GFM extended autolinks
- **WHEN** source contains `<scheme:...>`, `<email>`, `www.example.com`, bare URLs, or bare email addresses
- **THEN** links SHALL be produced per CommonMark/GFM rules including trailing-punctuation trimming
- **AND** destinations from inline links, reference links, and images SHALL pass the URL scheme allow-list (`http`/`https`/`mailto`/relative/`#fragment`); disallowed schemes render as literal text (no element)
- **AND** destinations from CommonMark angle-bracket autolinks and GFM extended autolinks SHALL be subject to a deny-list only (`javascript:`/`data:`/`vbscript:` render as literal text); any other syntactically valid scheme (e.g. `irc:`, `ftp:`, unknown schemes) produces a link per the GFM spec, because autolinks display their URL as text and thus carry no phishing surface

#### Scenario: GFM disallowed raw HTML
- **WHEN** source contains raw HTML tags in the GFM disallowed set (`title`, `textarea`, `style`, `xmp`, `iframe`, `noembed`, `noframes`, `script`, `plaintext`) as **inline HTML** or as **HTML blocks of types 2-7**
- **THEN** the leading `<` of those tags SHALL be entity-escaped (`&lt;`) in the Markdown→HTML output
- **AND** HTML blocks of **type 1** (`<script>`, `<pre>`, `<style>`, `<textarea>` raw-text containers) SHALL pass through verbatim, because the GFM spec suite pins verbatim output for those examples (filtering them would break conformance)
- **AND** the template binding layer's rejection of `script`/`style`/`iframe`/`noembed`/`noframes`/`xmp` remains as a separate, unchanged policy; note that `<textarea>`, `<title>`, and `<plaintext>` type-1 blocks are NOT rejected by the binding layer and therefore flow into the DOM verbatim (residual raw-HTML surface; rely on a downstream HTML sanitizer if Markdown is untrusted)

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

### Requirement: render_markdown shall support opt-in heading id injection

`render_markdown` SHALL accept a keyword-only `heading_ids: bool = False` option. When `True`, every `<h1>`–`<h6>` element in the rendered tree SHALL receive an `id` attribute containing a slug derived from the heading's text content. When `False` (default), heading elements SHALL be rendered exactly as today, preserving cmark-gfm conformance of the default output.

Slugs SHALL be generated as follows: Unicode-aware lowercasing, runs of whitespace replaced with single `-` characters, all characters that are not alphanumeric or `-` removed. Duplicate slugs within one document SHALL receive `-2`, `-3`, … suffixes in document order. Slug generation SHALL be deterministic for identical input.

#### Scenario: Heading ids injected when enabled

- **WHEN** `render_markdown("# Getting Started", heading_ids=True)` is called
- **THEN** the rendered `<h1>` element has `id="getting-started"`

#### Scenario: Default behavior unchanged

- **WHEN** `render_markdown("# Getting Started")` is called without options
- **THEN** the rendered `<h1>` element has no `id` attribute

#### Scenario: Duplicate heading slugs are deduplicated

- **WHEN** a document contains two headings with the same text and `heading_ids=True`
- **THEN** the first heading receives the base slug and the second receives the slug with a `-2` suffix

#### Scenario: Non-ASCII heading text

- **WHEN** a heading contains CJK characters and `heading_ids=True`
- **THEN** the slug retains the alphanumeric CJK characters so the heading remains addressable

### Requirement: render_markdown shall support opt-in code block highlighting

`render_markdown` SHALL accept a keyword-only `code_blocks: bool = False` option. When `True`, every `<pre>` element whose sole significant child is a `<code class="language-{lang}">` element SHALL be replaced by a `CodeBlock` component receiving the literal code text and `lang`. When `False` (default), fenced code blocks SHALL render as plain `<pre><code>` exactly as today.

The extracted code content SHALL remain literal: it MUST NOT be subject to `{{ }}` interpolation or directive processing at any point.

#### Scenario: Fenced code replaced with CodeBlock

- **WHEN** `render_markdown` is called with `code_blocks=True` on a document containing a ` ```python ` fenced block
- **THEN** the output tree contains a `CodeBlock` element with `lang="python"` and the literal code text instead of a `<pre><code>` subtree

#### Scenario: Default behavior unchanged

- **WHEN** `render_markdown` is called without options on a document containing a fenced block
- **THEN** the output contains a plain `<pre><code class="language-python">` subtree

#### Scenario: Code content stays literal

- **WHEN** a fenced block contains text resembling template syntax (e.g. `{{ name }}`) and `code_blocks=True`
- **THEN** the `CodeBlock` receives the text verbatim with no interpolation attempted

### Requirement: render_markdown shall support opt-in class map injection

`render_markdown` SHALL accept a keyword-only `classes: Mapping[str, str] | None = None` option mapping tag names to CSS class strings. When provided, every rendered element whose tag name is a key of the mapping SHALL have the mapped classes merged into its `class` attribute. Classes SHALL be merged additively with any classes already present on the element. When `None` (default), no classes are injected.

#### Scenario: Classes injected for mapped tags

- **WHEN** `render_markdown(source, classes={"table": "doc-table"})` renders a GFM table
- **THEN** the `<table>` element's `class` attribute includes `doc-table`

#### Scenario: Merge with existing classes

- **WHEN** an element already carries a class (e.g. `<code class="language-python">`) and its tag is mapped
- **THEN** the resulting `class` attribute contains both the original and the mapped classes

#### Scenario: Default behavior unchanged

- **WHEN** `render_markdown` is called without `classes`
- **THEN** rendered elements carry only the classes emitted by the parser today

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

The `render_markdown` pipeline SHALL detect whether a `{% for %}` body is a list body and route accordingly: list bodies → `MarkdownForElement`; non-list bodies → standard `repeat()`. List-body detection SHALL use the block parser's list-item start condition as its single source of truth (no separate marker regex), so detection and parsing can never diverge.

#### Scenario: List body detected and routed to MarkdownForElement
- **WHEN** a `{% for %}` body consists of list-item lines per the block grammar (`-`, `*`, `+`, or ordered markers, including task-list markers)
- **THEN** a `MarkdownForElement` SHALL be created

#### Scenario: Non-list body routed to repeat()
- **WHEN** a `{% for %}` body consists of heading lines (`#`), paragraphs (plain text), or HTML blocks (`<div>`)
- **THEN** the standard `repeat()` path SHALL be used (fully reactive with reactive `{% if %}`)

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

### Requirement: Template engine shall validate colon-prefixed attributes on HTML elements

On HTML elements, the recognized `:`-prefixed attributes SHALL be `:ref` and `:bind`. Any other `:`-prefixed attribute SHALL raise `WebComPyException` at bind time with a message naming the attribute and suggesting `{{ }}` interpolation as the alternative. The value resolved via `:ref` SHALL be a `DomNodeRef` instance; any other type SHALL raise `WebComPyException` at bind time naming the variable and its observed type. The value resolved via `:bind` SHALL be a writable `Signal` instance; any other type SHALL raise `WebComPyException` at bind time naming the variable and its observed type. Neither `:ref` nor `:bind` SHALL accept `{{ }}` interpolation inside the attribute value.

#### Scenario: Non-ref non-bind colon attribute rejected
- **WHEN** the template contains `<div :class="cls">`
- **THEN** `WebComPyException` SHALL be raised at bind time
- **AND** the message SHALL name `:class` and suggest using `class="{{ cls }}"` interpolation

#### Scenario: Ref binding type validation
- **WHEN** `render_template('<input :ref="r">', {"r": "not-a-ref"})` is called
- **THEN** `WebComPyException` SHALL be raised at bind time naming `r` and its observed type (`str`)

#### Scenario: Bind attribute resolves to a Signal
- **WHEN** `render_template('<input :bind="text">', {"text": Signal("hi")})` is called
- **THEN** the produced element SHALL behave exactly like `html.INPUT({":bind": text})` (two-way binding per the elements spec)

#### Scenario: Bind attribute type validation
- **WHEN** `render_template('<input :bind="text">', {"text": "literal"})` is called
- **THEN** `WebComPyException` SHALL be raised at bind time naming `text` and its observed type (`str`)

#### Scenario: Interpolation inside :bind rejected
- **WHEN** the template contains `<input :bind="{{ text }}">`
- **THEN** `WebComPyException` SHALL be raised at bind time stating `{{ }}` interpolation is not supported in `:bind` attributes

#### Scenario: Component tags unaffected
- **WHEN** a `:`-prefixed attribute appears on a component tag (e.g., `<user-card :count="n">`)
- **THEN** it SHALL continue to be bound as a dynamic prop (no error)

### Requirement: Template engine shall reject malformed HTML with descriptive errors

Mismatched closing tags, unclosed elements at end of input, and stray closing tags SHALL raise `WebComPyException` instead of being silently recovered or ignored. Error messages SHALL name the offending tag and, for mismatches, the expected open tag.

#### Scenario: Mismatched closing tag
- **WHEN** the template contains `<div><b>bold</div></b>`
- **THEN** `WebComPyException` SHALL be raised with a message indicating `</div>` was encountered while `<b>` was open

#### Scenario: Unclosed element at EOF
- **WHEN** the template contains `<div><p>hi` with no closing tags
- **THEN** `WebComPyException` SHALL be raised listing the unclosed tag(s)

#### Scenario: Stray closing tag
- **WHEN** the template contains `<div>text</span></div>`
- **THEN** `WebComPyException` SHALL be raised naming the stray `</span>`

### Requirement: Template engine shall provide descriptive errors for unsupported expressions and invalid iterables

Template-originated binding failures SHALL raise `WebComPyException` (not raw `TypeError`/`KeyError`) with the offending variable or expression named. Expression syntax errors and whitelist violations in `{{ }}` holes SHALL be reported at compile time; in `{% if %}`/`{% elif %}`/`{% for %}` directives they SHALL be reported at bind time. `{% for %}` targets that are not iterable SHALL produce an error naming the variable and its type. `{{ }}` spans matching brace syntax but failing expression parsing SHALL raise `WebComPyException` in text content and directive positions.

#### Scenario: Invalid expression in if condition
- **WHEN** the template contains `{% if a >> > b %}`
- **THEN** `WebComPyException` SHALL be raised at bind time naming the expression and the parse failure

#### Scenario: Non-iterable for target
- **WHEN** `{% for item in items %}` is used and `items` resolves to `None` or `5`
- **THEN** `WebComPyException` SHALL be raised naming `items` and its observed type

#### Scenario: Unsupported expression in hole
- **WHEN** the template contains `<p>{{ [x for x in items] }}</p>`
- **THEN** `WebComPyException` SHALL be raised at compile time stating that comprehensions are not supported

### Requirement: Template engine shall reject event handler attributes with modifiers

`@event` attribute names containing a modifier suffix (e.g., `@click.stop`, `@keyup.enter`) SHALL raise `WebComPyException` at bind time instead of registering a never-firing event name. The message SHALL name the attribute and state that event modifiers are not supported.

#### Scenario: Modifier rejected
- **WHEN** the template contains `<button @click.stop="handler">`
- **THEN** `WebComPyException` SHALL be raised naming `@click.stop` and stating that modifiers are not supported

### Requirement: Template AST cache shall distinguish parse functions

The template AST cache key SHALL incorporate the identity of the parse function, so that a custom `parse_fn` and the default parser never share a cache entry for the same source string.

#### Scenario: Custom parse function does not collide with default
- **WHEN** `render_template` is called with source `S` using the default parser, then with source `S` using a custom `parse_fn`
- **THEN** the custom `parse_fn` SHALL be invoked (not served the default parser's cached AST)

### Requirement: Markdown code blocks and code spans shall be protected from template processing

Fenced code blocks and inline code spans produced by `DefaultMarkdownParser` SHALL NOT be subject to `{{ }}` interpolation or `{% %}` directive execution when the resulting HTML is bound by `render_template`. Template-syntax-looking text inside code SHALL be rendered literally.

#### Scenario: Hole inside fenced code block
- **WHEN** `render_markdown` is called with a fenced code block containing `{{ x }}` and context `{"x": "secret"}`
- **THEN** the rendered `<pre><code>` content SHALL contain the literal text `{{ x }}`
- **AND** the value `secret` SHALL NOT appear in the output

#### Scenario: Directive inside fenced code block
- **WHEN** a fenced code block contains `{% if y %}text{% endif %}`
- **THEN** the directive SHALL NOT be executed
- **AND** the `<pre><code>` element SHALL remain a single intact block containing the literal directive text

#### Scenario: Hole inside inline code span
- **WHEN** a paragraph contains `` `{{ x }}` `` as a code span
- **THEN** the `<code>` content SHALL be the literal text `{{ x }}`

### Requirement: Markdown inline tokenization shall be order-independent and spoof-resistant

Inline Markdown processing SHALL correctly nest previously-tokenized elements inside later-tokenized ones regardless of processing order (e.g., italic containing bold, strikethrough containing bold). Internal placeholder keys SHALL never appear in rendered output, and SHALL be constructed so user input cannot collide with or spoof them.

#### Scenario: Italic containing bold
- **WHEN** the source contains `*a **b** c*`
- **THEN** the output SHALL be `<em>a <strong>b</strong> c</em>`
- **AND** no placeholder text (e.g., `__WEBCOMPY_INLINE_`) SHALL appear in the output

#### Scenario: Strikethrough containing bold
- **WHEN** the source contains `~~a **b** c~~`
- **THEN** the output SHALL be `<del>a <strong>b</strong> c</del>`

#### Scenario: Placeholder spoofing impossible
- **WHEN** the source text contains a string resembling an internal placeholder key alongside real inline markup
- **THEN** the literal user text SHALL be preserved as-is
- **AND** only genuine markup SHALL be converted

### Requirement: Markdown links and images shall restrict URL schemes

`DefaultMarkdownParser` SHALL only emit `href`/`src` attributes for URLs with an allowed scheme: `http:`, `https:`, `mailto:`, relative URLs (no scheme), and fragment identifiers (`#...`). URLs with any other scheme (including `javascript:`, `data:`, `vbscript:`) SHALL NOT produce a link or image element; the link text SHALL be rendered as plain text instead.

#### Scenario: javascript URL neutralized
- **WHEN** the source contains `[click](javascript:alert(1))`
- **THEN** no `<a>` element with a `javascript:` href SHALL be emitted
- **AND** the text `click` SHALL be rendered as plain text

#### Scenario: Allowed schemes unaffected
- **WHEN** the source contains links with `https:`, `http:`, `mailto:`, relative (`/docs`, `./page.md`), and fragment (`#section`) URLs
- **THEN** all SHALL render as normal `<a href>` elements

### Requirement: Markdown list handling shall be consistent and lossless

The block parser SHALL recognize `+` as an unordered list marker (consistent with the for-body list detector). Multi-line list-item text SHALL be joined with a single space. Ordered lists SHALL preserve the first item's number via a `start` attribute when it differs from 1. Spaced horizontal-rule patterns (`* * *`, `- - -`, `_ _ _`) SHALL be recognized as `<hr>` before list or paragraph handling.

#### Scenario: Plus-marker list
- **WHEN** the source contains `+ one` and `+ two`
- **THEN** the output SHALL be `<ul><li>one</li><li>two</li></ul>`

#### Scenario: Plus-marker for-loop body
- **WHEN** `render_markdown` processes `{% for i in items %}` with body lines starting with `+ `
- **THEN** the merged output SHALL be a single `<ul>` with `<li>` children (not paragraphs)

#### Scenario: Multi-line list item
- **WHEN** the source contains `- foo` followed by an indented continuation line `  bar`
- **THEN** the output SHALL be `<li>foo bar</li>` (single-space joined)

#### Scenario: Ordered list start number
- **WHEN** the source contains `3. three` and `4. four`
- **THEN** the output SHALL be `<ol start="3"><li>three</li><li>four</li></ol>`

#### Scenario: Spaced horizontal rule
- **WHEN** the source contains `* * *` or `- - -` on its own line
- **THEN** the output SHALL be `<hr>` (not a `<ul>` or paragraph)

### Requirement: Template expression language limitations shall be documented

The template expression grammar is a safe Python-expression subset (per the expression-language requirement). Comprehensions, lambdas, assignment expressions, Jinja2 tests (`is defined`), the `~` operator, and custom filter registration are unsupported, as stated in this spec. Method calls from templates can mutate state (developer-authored templates, same exposure as Jinja2). Filter names take precedence over context variables on the right of `|`. This requirement is self-contained: the spec itself is the authoritative documentation and SHALL NOT reference external documentation pages.

#### Scenario: Unsupported syntax errors, not silent output
- **WHEN** a template uses a comprehension, lambda, or walrus expression
- **THEN** a descriptive `WebComPyException` SHALL be raised at compile time (per the error-quality requirement)
- **AND** this spec SHALL list these constructs as unsupported

#### Scenario: Filter precedence documented
- **WHEN** a context variable shares its name with a registered filter
- **THEN** the registered filter SHALL take precedence on the right of `|` (as stated in this spec)

### Requirement: For-loop semantics limitations shall be documented

One-variable iteration over a dict (`{% for v in my_dict %}`) iterates **values** (not keys, matching the `repeat()` overload contract). Two-variable unpacking is supported only for dict iterables. `{% else %}` on for, `break`/`continue`, and iteration over `list[tuple]` with unpacking are NOT supported, as stated in this spec. Loop metadata (`loop.index` and related attributes) IS supported per the loop-metadata requirement. This requirement is self-contained: the spec itself is the authoritative documentation and SHALL NOT reference external documentation pages.

#### Scenario: Dict value iteration is the contract

- **WHEN** `{% for v in my_dict %}` is used with a dict or `ReactiveDict`
- **THEN** `v` SHALL bind to each value (an intentional divergence from Python's key iteration, stated in this spec)

#### Scenario: for-else remains unsupported
- **WHEN** a template places `{% else %}` inside a `{% for %}` block
- **THEN** it SHALL be treated as a malformed control-flow structure (error or rejection), NOT as Jinja2's empty-iteration branch

### Requirement: Scoped-CSS limitations shall be documented

Selectors targeting `:root`, `html`, or `body` in `scoped_style`/`css_text` are dead rules (the cid attribute exists only on component elements); use app-level styles (`app.style`) instead. Duplicate selectors/properties/at-rule keys in `css_text` source are last-wins. Statement at-rules (`@import`, `@charset`) are dropped. Keyframe names are global (same-named `@keyframes` in different components collide). This requirement is self-contained: the spec itself is the authoritative documentation and SHALL NOT reference external documentation pages.

#### Scenario: :root rule documented as inert

- **WHEN** a developer writes `:root { --x: 1; }` in scoped CSS
- **THEN** the rule SHALL be emitted scoped (`:root[cid]`, matching nothing)
- **AND** the spec's recommendation SHALL be to use app-level styles (`app.style`) instead

### Requirement: HTML parsing limitations shall be documented

SVG/MathML foreign content is unsupported (tag/attribute case is lowercased, breaking case-sensitive SVG names like `viewBox`/`linearGradient`, and elements are created without namespace support); construct SVG via `raw_html()` or the element API instead. `textwrap.dedent` interacts destructively with intentional indentation inside `<pre>` in triple-quoted templates. HTML entities decoded by the parser (e.g., `&#123;`) become live `{{ }}` holes; `{% raw %}` is the correct literal-`{{` mechanism. `{# ... #}` spans inside Markdown raw-HTML passthrough blocks are stripped (matching Jinja2 comment behavior), while Markdown code blocks/spans remain protected. This requirement is self-contained: the spec itself is the authoritative documentation and SHALL NOT reference external documentation pages.

#### Scenario: SVG case corruption documented
- **WHEN** a template contains `<svg viewBox="0 0 1 1">`
- **THEN** the attribute SHALL be lowercased (`viewbox`)
- **AND** the spec's recommendation SHALL be to construct SVG via `raw_html()` or the element API instead

#### Scenario: Entity-decoded hole documented
- **WHEN** a template contains `&#123;&#123; x &#125;&#125;` with `x` in the context
- **THEN** the decoded `{{ x }}` SHALL be interpolated
- **AND** the spec's direction SHALL be to use `{% raw %}` for literal `{{` output

#### Scenario: Markdown raw-HTML comment stripping documented
- **WHEN** a Markdown raw-HTML block contains `{# ... #}`
- **THEN** the span SHALL be stripped during template binding
- **AND** this spec SHALL state it as intentional, matching Jinja2 comment semantics
