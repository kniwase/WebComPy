# Delta: template-engine

## ADDED Requirements

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

#### Scenario: ReactiveDict value that is an Element rendered as child
- **WHEN** `{% for v in d %}{{ v }}{% endfor %}` is used with a `ReactiveDict` whose values include `Element` or `Component` instances
- **THEN** each Element/Component SHALL be placed as a direct child element (not stringified)
- **AND** scalar values SHALL continue to render as text with reactive updates

#### Scenario: ReactiveDict loop value keeps fresh value semantics
- **WHEN** a `ReactiveDict` key is updated with a new value (including a nested `Signal` value) while a loop over the dict is rendered
- **THEN** the loop body SHALL observe the current stored value (not a stale callback argument), unwrapping nested `Signal` values
- **AND** the rendered content SHALL update reactively

### Requirement: Dotted paths shall unwrap intermediate Signals

Multi-segment plain paths (e.g., `{{ user.profile.name }}`) SHALL unwrap a `SignalBase` encountered at any intermediate segment (read `.value`) and continue resolving the remaining segments. When an intermediate segment resolves to a Signal, the resolution SHALL be wrapped in an implicit `Computed` so downstream text updates reactively when the Signal changes. Single-segment plain paths that resolve to a Signal SHALL pass the Signal through unwrapped (no `Computed`).

#### Scenario: Dotted path with intermediate Signal
- **WHEN** `{{ user.profile.name }}` is used where `user.profile` resolves to a `Signal({"name": "Alice"})`
- **THEN** the intermediate Signal SHALL be unwrapped (`.value` read) and the remaining segment `name` SHALL resolve to `"Alice"`

#### Scenario: Reactive dotted path with intermediate Signal
- **WHEN** `{{ user.profile.name }}` has an intermediate `Signal` at the `.profile` position and that Signal is updated
- **THEN** the rendered text SHALL update reactively via an implicit `Computed` that re-resolves the remaining segments through the unwrapped Signal

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

## MODIFIED Requirements

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
