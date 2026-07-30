# Delta: template-engine

## ADDED Requirements

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

Each hole, condition, or iterable target SHALL be classified at bind time. A **plain path** (only `Name`/`Attribute` chain) SHALL behave exactly as before: a resolved Signal is passed through unwrapped. A **true expression** (any other form) whose referenced context values include a `SignalBase` SHALL be wrapped in a `Computed` closure that re-evaluates the expression; a true expression without Signal references SHALL be evaluated once. During expression evaluation, encountering a `SignalBase` SHALL read `.value` (unwrap), registering the dependency via the active-consumer mechanism. Unwrapping a `ReactiveList`/`ReactiveDict` yields the raw collection (coarse dependency).

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

## MODIFIED Requirements

### Requirement: Template engine shall support variable interpolation in text content

`{{ varname }}` and `{{ a.b.c }}` (dot notation) SHALL interpolate variables from the context into text content; these plain paths SHALL pass Signal values directly to `TextElement` for reactive updates. `{{ }}` holes SHALL additionally accept the safe expression subset (per the expression-language requirement), with Signal-referencing expressions wrapped in an implicit `Computed`.

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

#### Scenario: Expression in text content
- **WHEN** `render_template("<p>{{ price * quantity }}</p>", {"price": 100, "quantity": 3})` is called
- **THEN** the text content SHALL be `"300"`

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

### Requirement: Template expression language limitations shall be documented

The template expression grammar SHALL be documented as a safe Python-expression subset (per the expression-language requirement). Comprehensions, lambdas, assignment expressions, Jinja2 tests (`is defined`), the `~` operator, and custom filter registration SHALL be documented as unsupported. Method calls from templates SHALL be documented as able to mutate state (developer-authored templates, same exposure as Jinja2). Filter-name precedence over context variables on the right of `|` SHALL be documented.

#### Scenario: Unsupported syntax errors, not silent output
- **WHEN** a template uses a comprehension, lambda, or walrus expression
- **THEN** a descriptive `WebComPyException` SHALL be raised at compile time (per the error-quality requirement)
- **AND** the framework documentation SHALL list these constructs as unsupported

#### Scenario: Filter precedence documented
- **WHEN** a context variable shares its name with a registered filter
- **THEN** the documentation SHALL state that the filter registry takes precedence on the right of `|`

### Requirement: HTML parsing limitations shall be documented

SVG/MathML foreign content SHALL be documented as unsupported (tag/attribute case is lowercased, breaking case-sensitive SVG names like `viewBox`/`linearGradient`, and elements are created without namespace support). `textwrap.dedent` SHALL be documented as interacting destructively with intentional indentation inside `<pre>` in triple-quoted templates. HTML entities decoded by the parser (e.g., `&#123;`) SHALL be documented as becoming live `{{ }}` holes, with `{% raw %}` documented as the correct literal-`{{` mechanism. `{# ... #}` spans inside Markdown raw-HTML passthrough blocks SHALL be documented as being stripped (matching Jinja2 comment behavior), while Markdown code blocks/spans remain protected.

#### Scenario: SVG case corruption documented
- **WHEN** a template contains `<svg viewBox="0 0 1 1">`
- **THEN** the attribute SHALL be lowercased (`viewbox`)
- **AND** the documentation SHALL recommend constructing SVG via `raw_html()` or the element API instead

#### Scenario: Entity-decoded hole documented
- **WHEN** a template contains `&#123;&#123; x &#125;&#125;` with `x` in the context
- **THEN** the decoded `{{ x }}` SHALL be interpolated
- **AND** the documentation SHALL direct users to `{% raw %}` for literal `{{` output

#### Scenario: Markdown raw-HTML comment stripping documented
- **WHEN** a Markdown raw-HTML block contains `{# ... #}`
- **THEN** the span SHALL be stripped during template binding
- **AND** this SHALL be documented as intentional, matching Jinja2 comment semantics
