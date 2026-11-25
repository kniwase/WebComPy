---
title: Jinja2 Compatibility Notes
description: Complete matrix mapping Jinja2 directives, filters, expressions, tests, and HTML behavior to WebComPy's reactive template compiler with exact exception messages.
---

# Jinja2 Compatibility Notes

WebComPy's [`render_template()`](/documents/basic/template-html) looks familiar to Jinja2 authors by design, yet compiles into a reactive WebComPy `Element` tree rather than concatenating server-side strings. Every difference below stems from two strict design rules: **composition belongs in Python components/slots**, and **expressions use a safe AST-whitelisted Python subset**.

For strategy and architecture guidance, start with [Migrating from Jinja2 + FastAPI](/documents/migration/from-jinja2-fastapi).

## Supported constructs

These Jinja2 constructs work identically inside `render_template()` (and gain automatic reactive updates whenever an expression touches a `Signal`, `Computed`, `ReactiveList`, or `ReactiveDict`):

| Construct | Syntax | Behavior in WebComPy |
|---|---|---|
| Text & attribute interpolation | `{{ user.name }}`, `class="tab {{ active_cls }}"` | Unwraps `Signal`s transparently; non-trivial expressions wrap in an owned `Computed` |
| Conditionals | `{% if cond %}...{% elif other %}...{% else %}...{% endif %}` | Renders reactively via `SwitchElement` when any branch condition reads a signal |
| Loops | `{% for item in items %}...{% endfor %}` and `{% for k, v in mapping %}...{% endfor %}` | Expands list/dict loops statically, or reactively via `repeat()` for `ReactiveList`/`ReactiveDict`/`Computed` |
| Loop metadata | `loop.index`, `loop.index0`, `loop.revindex`, `loop.revindex0`, `loop.first`, `loop.last`, `loop.length` | Matches Jinja2 attributes (see unsupported `loop.*` methods below for exceptions) |
| Template comments | `{# developer note #}` | Stripped before directive and expression parsing; HTML `<!-- ... -->` comments are also omitted from DOM nodes |
| Verbatim raw blocks | `{% raw %}{{ literal }}{% endraw %}` | Protects literal `{{` / `{%` text from interpolation and directive scanning |
| Standard Python operators | `+`, `-`, `*`, `/`, `//`, `%`, `**`, `==`, `!=`, `<`, `<=`, `>`, `>=`, `in`, `not in`, `is None`, `is not None`, `and`, `or`, `not`, `a if c else b` | Evaluated via AST node whitelist (never `eval()`) |

## Rejected directives and exact errors

All structural, variable-assignment, and i18n directives in Jinja2 are **rejected at compile time** with `WebComPyException` rather than silently ignored. Search your error message below to locate the exact WebComPy pattern:

| Jinja2 directive | Status | Exact error raised | WebComPy replacement |
|---|---|---|---|
| `extends` | **Rejected** | `WebComPyException: {% extends %} is not supported in WebComPy templates` | Wrap child routes via `RouterView()` inside a layout component, or wrap shell content in `slots` ([Routing](/documents/basic/routing)) |
| `block` | **Rejected** | `WebComPyException: {% block %} is not supported in WebComPy templates` | Define named slots via `context.slots("header", fallback=...)` inside a `@define_component()` ([Components](/documents/basic/components#props-and-slots)) |
| `endblock` | **Rejected** | `WebComPyException: {% endblock %} is not supported in WebComPy templates` | Closing tag of a Python component slot / child element |
| `macro` | **Rejected** | `WebComPyException: {% macro %} is not supported in WebComPy templates` | Extract a `@define_component()` or a plain Python helper returning `html.*` / `render_template(...)` ([Components](/documents/basic/components)) |
| `endmacro` | **Rejected** | `WebComPyException: {% endmacro %} is not supported in WebComPy templates` | End of Python helper function or component |
| `call` | **Rejected** | `WebComPyException: {% call %} is not supported in WebComPy templates` | Render `<my-widget>slot content</my-widget>` component tags or pass `slots={"default": lambda: ...}` ([HTML Templates](/documents/basic/template-html#component-tags-in-templates)) |
| `endcall` | **Rejected** | `WebComPyException: {% endcall %} is not supported in WebComPy templates` | Closing `</my-widget>` tag |
| `include` | **Rejected** | `WebComPyException: {% include %} is not supported in WebComPy templates` | Define a child component and render `<child-partial />` or call it in Python |
| `import` | **Rejected** | `WebComPyException: {% import %} is not supported in WebComPy templates` | Use standard Python `import` at module or component setup scope |
| `from` | **Rejected** | `WebComPyException: {% from %} is not supported in WebComPy templates` | Use standard Python `from ... import ...` in component code |
| `set` | **Rejected** | `WebComPyException: {% set %} is not supported in WebComPy templates` | Compute local Python variables or `Computed(...)` / `use_computed(...)` before passing `ctx` ([Reactive State](/documents/basic/reactive-state)) |
| `with` | **Rejected** | `WebComPyException: {% with %} is not supported in WebComPy templates` | Compute scoped Python variables in a helper function or component setup |
| `endwith` | **Rejected** | `WebComPyException: {% endwith %} is not supported in WebComPy templates` | End of Python helper scope |
| `filter` | **Rejected** | `WebComPyException: {% filter %} is not supported in WebComPy templates` | Pipe single expressions `{{ text \| upper }}` or pre-transform strings in Python |
| `endfilter` | **Rejected** | `WebComPyException: {% endfilter %} is not supported in WebComPy templates` | End of Python string transformation |
| `do` | **Rejected** | `WebComPyException: {% do %} is not supported in WebComPy templates` | Mutate reactive lists/dicts inside Python event handlers or `@on_before_rendering` |
| `trans` | **Rejected** | `WebComPyException: {% trans %} is not supported in WebComPy templates` | Pass translated signals/strings from `use_i18n()` into template context ([Internationalization](/documents/advanced/i18n)) |
| `endtrans` | **Rejected** | `WebComPyException: {% endtrans %} is not supported in WebComPy templates` | Use `use_i18n()` catalog lookups |
| `pluralize` | **Rejected** | `WebComPyException: {% pluralize %} is not supported in WebComPy templates` | Use `t(key, count=...)` from `use_i18n()` with pipe-separated plural rules |
| `autoescape` | **Rejected** | `WebComPyException: {% autoescape %} is not supported in WebComPy templates` | WebComPy always creates escaped DOM text nodes; opt in intentionally with `raw_html()` |
| `endautoescape` | **Rejected** | `WebComPyException: {% endautoescape %} is not supported in WebComPy templates` | Control raw HTML insertion explicitly per element |
| `debug` | **Rejected** | `WebComPyException: {% debug %} is not supported in WebComPy templates` | Inspect context in Python logs or browser DevTools / `webcompy inspect console` |
| Any unrecognized directive (`foo`) | **Rejected** | `WebComPyException: Unknown template directive: {% foo %}` | Use only `{% if %}`, `{% elif %}`, `{% else %}`, `{% endif %}`, `{% for %}`, `{% endfor %}`, `{% raw %}`/`{% endraw %}` |
| `{% for x in items %}...{% else %}...{% endfor %}` | **Rejected** | `WebComPyException: {% else %} outside of {% if %} block` | Guard the loop with `{% if items %}...{% for ... %}{% endfor %}{% else %}...{% endif %}` |

## Built-in filters and filter differences

WebComPy implements **16** built-in pipeline filters in `webcompy.template._expression.FILTERS`:

| Filter | Status vs Jinja2 | Exact signature & behavior difference |
|---|---|---|
| `upper` | **Supported identically** | `str(v).upper()` |
| `lower` | **Supported identically** | `str(v).lower()` |
| `title` | **Supported identically** | `str(v).title()` |
| `capitalize` | **Supported identically** | `str(v).capitalize()` |
| `trim` | **Supported identically** | `str(v).strip()` (note: accepts no argument, unlike Jinja2's optional `chars`) |
| `length` | **Supported / Renamed (`count` absent)** | `len(v)` (Jinja2's `count` alias is not in `FILTERS`) |
| `join` | **Supported** | `sep.join(str(x) for x in v)` with default `sep=""` (no Jinja2 `attribute=` keyword) |
| `default` | **Behavior differs** | `d if v is None else v` (`default=""`). Checks **`v is None` only** — falsy strings/zeros return as-is, and passing `boolean=True` raises `WebComPyException` (`unexpected keyword argument 'boolean'`). Use Python ternary `{{ v or "fallback" }}` when falsy values should fall back. |
| `replace` | **Restricted args** | `str(v).replace(old, new)` (no `count=` parameter) |
| `round` | **Restricted args** | `round(v, ndigits)` (`ndigits=None`; no `method=` parameter) |
| `int` | **Supported** | `int(v)` (no `default=` or `base=` kwargs) |
| `float` | **Supported** | `float(v)` (no `default=` kwarg) |
| `string` | **Supported identically** | `str(v)` |
| `first` | **Behavior differs** | Indexes `v[0]` directly rather than safely yielding empty/undefined on empty sequences or iterators |
| `last` | **Behavior differs** | Indexes `v[-1]` directly rather than iterating generators |
| `abs` | **Supported identically** | `abs(v)` |

### Missing and custom Jinja2 filters (`| safe`, `| escape`, `| sort`, ...)

WebComPy does **not** have a Jinja2 environment filter registry beyond the 16 filters above. When `x | my_filter` names an identifier absent from `FILTERS`, the compiler parses `|` as Python bitwise OR (`ast.BitOr`) and looks up `my_filter` as a variable in `ctx`:

- `{{ snippet | safe }}` → `KeyError: "Template variable 'safe' not found in context (available: ...)"`. Replacement: [`raw_html(snippet)`](/documents/basic/elements-and-events) for trusted markup.
- `{{ text | escape }}` / `{{ text | e }}` → `KeyError` on `escape`/`e`. WebComPy automatically creates safe text nodes via `document.createTextNode`, so no `| escape` filter is needed.
- `{{ items | sort }}`, `| tojson`, `| truncate`, `| urlencode`, or custom Django/Jinja2 filters → precompute a `Computed` signal or expose a regular Python helper function in `ctx` and call it directly: `{{ format_currency(price) }}` or `{{ sorted_items }}`.

## Expressions, tests, and template differences

### Jinja2 `is` tests (`is defined`, `is odd`, `is none`)

Jinja2's `is <test>` syntax is not special-cased; WebComPy compiles Python `is` (`ast.Is`). Consequently:

- `{{ user is defined }}` parses as `user is defined` and looks up `defined` in `ctx`, raising:
  `KeyError: "Template variable 'defined' not found in context (available: ...)"`
- `{{ loop.index is odd }}` raises `KeyError: "Template variable 'odd' not found in context (available: ...)"`
- `{{ val is none }}` (lowercase) raises `KeyError` on `none` — use Python `None` (`{{ val is None }}` or `{{ val is not None }}`).
- For optional keys, test `"user" in ctx_dict` or pass explicit booleans/defaults from Python instead of `is defined`.

### String concatenation with `~`

Jinja2's `{{ first ~ " " ~ last }}` uses the `~` binary operator, which is bitwise NOT (unary only) in Python:

- Exact error: `WebComPyException: Invalid template expression 'first ~ " " ~ last': invalid syntax ...`
- Replacement: use `+` on strings (`{{ first + " " + last }}`) or compute a formatted `Computed` string in Python.

### Missing variables (strict `KeyError`, not silent `Undefined`)

Jinja2 renders missing names as empty strings by default. WebComPy rejects missing context names strictly:

- Exact error: `KeyError: "Template variable '<name>' not found in context (available: ...)"`
- Replacement: supply explicit defaults in your context dictionary or use `dict.get("key", "")`.

### Disallowed Python AST syntax inside `{{ ... }}`

To avoid arbitrary code injection in template strings, only safe expression AST nodes are allowed (no comprehensions, `lambda`, walrus `:=`, f-strings, or `await`):

- Comprehensions / `lambda` / `:=` / f-strings → `WebComPyException: Unsupported construct in template expression '<expr>': <NodeType> is not allowed`
- Leading underscore attribute (`{{ obj._secret }}`, `{{ obj.__class__ }}`) → `WebComPyException: Dunder/private attribute access not allowed in template expression '<expr>': <attr>`
- Dynamic callable subscript (`{{ handlers[0]() }}`) → `WebComPyException: Indirect call is not allowed in template expression '<expr>'`

### Unsupported `loop.*` methods

WebComPy provides `index`, `index0`, `revindex`, `revindex0`, `first`, `last`, and `length` on `loop`. Calling Jinja2's `loop.cycle(...)`, `loop.previtem`, `loop.nextitem`, `loop.depth`, or `loop.changed(...)` raises:

- Exact error: `WebComPyException: Error evaluating template expression 'loop.<attr>...': 'LoopMetadata' object has no attribute '<attr>'`
- Replacement: use `loop.index0 % 2` (CSS `:nth-child` / ternary class) or compute adjacent items in Python before rendering.

### HTML container, tag, and binding restrictions

| Jinja2 pattern | WebComPy error raised | WebComPy replacement |
|---|---|---|
| Multiple top-level nodes (`<h1>Hi</h1><p>...</p>`) in `render_template()` | `WebComPyException: Template must have exactly one root element` | Wrap in a single container (`<div>...</div>`) or return a `list` of `html.*` elements from your `@define_component()` |
| `<script>`, `<style>`, `<iframe>`, `<noembed>`, `<noframes>`, `<xmp>` inside templates | `WebComPyException: <script> is not allowed in templates. Use scoped_style() for CSS or raw_html() for controlled HTML insertion.` (same format per tag) | Use `Component.scoped_style`, `app.scripts`, or Python `html.IFRAME(...)` where an intentional sandboxed embed is built in Python |
| Vue/Alpine-style modifiers (`@click.prevent`, `@keydown.enter`) | `WebComPyException: Event modifiers are not supported in templates: '@click.prevent'. Use the plain event name '@click' and handle the modifier logic inside the handler.` | Call `ev.preventDefault()` or inspect `ev.key` inside your Python event handler |
| Arbitrary `:`-prefixed HTML attrs (`:href="url"`, `:class="cls"`) | `WebComPyException: Unsupported attribute ':href' on HTML element: only ':ref' and ':bind' are allowed for ':'-prefixed attributes. Use {{ }} interpolation instead, e.g. href="{{ ... }}".` | Use `href="{{ url }}"` and `class="{{ cls }}"` interpolation on HTML tags (`:` props apply only to hyphenated `<my-component>` tags) |
| Unknown hyphenated tag (`<user-card>`) without registration | `WebComPyException: Component 'UserCard' not found for tag <user-card>. ...` | Define and import `@define_component() def UserCard(...)` before rendering, or pass `custom_element_name=` |
| Whitespace trim markers (`{%- if x -%}`) | **Behavior differs (not stripped)**: stays literal text instead of executing directive | Use plain `{% if x %}` without `-`; HTML DOM whitespace rarely matches Jinja2 text emission |
| Jinja2 `url_for()` global | `KeyError: "Template variable 'url_for' not found in context ..."` | Use [`RouterLink`](/documents/basic/routing) / `<router-link>` and static paths relative to `WebComPyAppConfig.base_url` |

## Next steps

- Return to [Migrating from Jinja2 + FastAPI](/documents/migration/from-jinja2-fastapi) for integration strategies, the live before/after comparison, and the strangler checklist.
- Review the full template surface in [HTML Templates](/documents/basic/template-html).
- Explore component props/slots in [Components](/documents/basic/components) and computed signals in [Reactive State](/documents/basic/reactive-state).
- Inspect the template AST and parser functions in [Template & Markdown API](/documents/api/template-and-markdown).
