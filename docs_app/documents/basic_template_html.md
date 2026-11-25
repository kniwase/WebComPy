---
title: HTML Templates
description: Render WebComPy Element trees from HTML strings with reactive {{ }} interpolation, safe expressions, filters, conditionals, loops, events, and component tags.
---

# HTML Templates

`render_template()` lets you write HTML markup instead of nested `html.DIV(...)` calls. It parses your template string at compile time using Python's `html.parser.HTMLParser` and returns a standard WebComPy `Element` tree with full reactive bindings preserved.

Use HTML templates whenever a component view reads more cleanly as HTML, while keeping Python components and slots for composition.

## At a glance

Pass an HTML template string (with a single root element) and a context dictionary to `render_template`:

```python
from webcompy.components import ComponentContext, define_component
from webcompy.signal import Signal
from webcompy.template import render_template


@define_component()
def CounterBanner(context: ComponentContext[None]):
    count = Signal(0)

    def increment(_ev):
        count.value += 1

    return render_template(
        """
        <section class="banner">
            <h2>Counter: {{ count }}</h2>
            <button @click="increment">+1</button>
        </section>
        """,
        {"count": count, "increment": increment},
    )
```

## Interpolation and reactivity

Use `{{ expr }}` in text content or HTML attribute values:

- **Direct Signal reference**: `{{ count }}` passes the `Signal` directly into a reactive text node or attribute — updates are surgical with zero intermediate wrapper.
- **Expression or dotted path through a Signal**: expressions like `{{ count * 2 }}`, `{{ "even" if count % 2 == 0 else "odd" }}`, or `{{ user.profile.name }}` when `profile` is a `Signal` automatically wrap in an implicit `Computed` so the DOM updates whenever any referenced Signal changes.
- **Static context values**: plain strings, numbers, `Element`, and `Component` objects are inserted directly without extra reactive overhead. A `None` variable renders nothing in text positions and `""` in attribute interpolation.
- **Boolean attributes**: valueless attributes such as `<button disabled>` become `disabled=True`; `<img alt="">` stays `""`.

```python
render_template(
    '<div class="card {{ active_cls }}" style="width: {{ pct }}%"><input disabled></div>',
    {"active_cls": active_cls, "pct": pct},
)
```

## Safe expression subset and built-in filters

Inside `{{ ... }}`, WebComPy accepts a safe AST-whitelisted Python expression subset:

- Attribute access (`user.name`), dict/sequence subscripting (`items[0]`, `data["key"]`), arithmetic/comparison/boolean operators (`+`, `==`, `in`, `not`, `and`, `or`), conditional expressions (`a if cond else b`), container literals, and plain method/function calls (`name.upper()`).
- Private attribute names starting with `_`, comprehensions, lambdas, and assignment expressions (`:=`) are rejected at compile time.

You can pipe values through the 16 built-in Jinja2-style filters (`{{ value | upper }}`, chained with arguments like `{{ items | join(", ") }}`):

| Filter | Signature / Example | Behavior |
|---|---|---|
| `upper` | `{{ s \| upper }}` | `str(val).upper()` |
| `lower` | `{{ s \| lower }}` | `str(val).lower()` |
| `title` | `{{ s \| title }}` | `str(val).title()` |
| `capitalize` | `{{ s \| capitalize }}` | `str(val).capitalize()` |
| `trim` | `{{ s \| trim }}` | `str(val).strip()` |
| `length` | `{{ seq \| length }}` | `len(val)` |
| `join` | `{{ seq \| join(", ") }}` | Join iterable elements with separator (default `""`) |
| `default` | `{{ val \| default("n/a") }}` | Fallback if `val is None` (or falsy when `boolean=True`) |
| `replace` | `{{ s \| replace("a", "b") }}` | `str(val).replace(old, new)` |
| `round` | `{{ n \| round(2) }}` | `round(val, precision)` |
| `int` | `{{ val \| int }}` | `int(val)` |
| `float` | `{{ val \| float }}` | `float(val)` |
| `string` | `{{ val \| string }}` | `str(val)` |
| `first` | `{{ seq \| first }}` | First item of non-empty sequence, else `None` |
| `last` | `{{ seq \| last }}` | Last item of non-empty sequence, else `None` |
| `abs` | `{{ n \| abs }}` | `abs(val)` |

## Conditionals and loops

### Conditionals (`{% if %}`)

Branch blocks using `{% if %}`, optional `{% elif %}`, optional `{% else %}`, and `{% endif %}`. When a condition reads a `Signal` (or `ReactiveList`/`ReactiveDict`), the template binds a reactive switch node automatically:

```html
<div>
    {% if user.logged_in %}
        <p>Welcome back, {{ user.name }}.</p>
    {% elif loading %}
        <p>Loading profile...</p>
    {% else %}
        <a href="/login">Sign in</a>
    {% endif %}
</div>
```

### Loops (`{% for %}`) and `loop` metadata

Iterate over lists, iterables, reactive collections, or dicts (with two variables `{% for key, value in mapping %}`):

```html
<ul>
    {% for item in items %}
        <li>{{ loop.index }}. {{ item }}</li>
    {% endfor %}
</ul>
```

When you reference `loop` inside the loop body, WebComPy exposes iteration metadata matching Jinja2's `loop` object:

| Property | Meaning |
|---|---|
| `loop.index` | 1-based iteration count (`1`, `2`, ...) |
| `loop.index0` | 0-based iteration count (`0`, `1`, ...) |
| `loop.revindex` | Iterations remaining including current (`length` down to `1`) |
| `loop.revindex0` | Iterations remaining after current (`length - 1` down to `0`) |
| `loop.first` | `True` on the first iteration |
| `loop.last` | `True` on the last iteration |
| `loop.length` | Total number of items |

## Comments and raw blocks

- **HTML comments**: `<!-- ... -->` are stripped during parsing and emit no DOM nodes.
- **Template comments**: `{# developer note #}` are stripped before expression/directive compilation.
- **Raw blocks**: wrap literal `{{` or `{%` text inside `{% raw %}...{% endraw %}` so it renders untouched as plain text:

```html
<code>{% raw %}{{ variable }}{% endraw %}</code>
```

## Events, `:ref`, and `:bind` attributes

Special attribute prefixes connect HTML elements directly to Python behavior:

| Attribute syntax | Expects in context | Behavior |
|---|---|---|
| `@click="handler"` (any `@<event>`) | Callable or `async def` handler | Registers DOM event listener receiving `DOMEvent` |
| `:ref="input_ref"` | `DomNodeRef` instance | Captures the mounted DOM node in `input_ref` |
| `:bind="text_signal"` | Writable `Signal` (use Python `html.*` for `Field`) | Two-way binds input/textarea/select value or checkbox/radio checked state |

```python
from webcompy.elements import DomNodeRef
from webcompy.signal import Signal
from webcompy.template import render_template

name = Signal("")
input_ref = DomNodeRef()


def focus_input(_ev):
    input_ref.focus()


render_template(
    """
    <div>
        <input :ref="input_ref" :bind="name" placeholder="Your name">
        <button type="button" @click="focus_input">Focus</button>
        <p>Hello {{ name | default("stranger") }}</p>
    </div>
    """,
    {"name": name, "input_ref": input_ref, "focus_input": focus_input},
)
```

Only `:ref` and `:bind` are valid `:`-prefixed attributes on standard HTML elements. To compute regular HTML attributes dynamically, use `{{ ... }}` (e.g., `class="{{ item_class }}"`).

## Component tags in templates

Any hyphenated tag not in standard HTML (such as `<user-card>`) resolves via the application's component registry by converting kebab-case to PascalCase (`<user-card>` → `UserCard`). Plain attributes become string props, `:`-prefixed props pass context variables (preserving Signals), and element children become the component's `"default"` slot:

```html
<div>
    <user-card title="Profile" :item-count="count">
        <p>Shown inside the default slot.</p>
    </user-card>
</div>
```

Note that `:`-prefixed prop names convert kebab-case to snake_case in `context.props` (`:item-count` → `context.props["item_count"]`).

## Notes & caveats

- **Single root element**: `render_template()` requires exactly one top-level root element (`<div>...</div>`). Return multiple roots at the component boundary with a Python `list` if needed.
- **Rejected HTML tags**: `<script>`, `<style>`, `<iframe>`, `<noembed>`, `<noframes>`, and `<xmp>` raise `WebComPyException`. Use component `scoped_style` for CSS or `raw_html()` when explicitly rendering trusted markup.

> **Not full Jinja2 — unsupported directives raise an error**: WebComPy's template engine uses Python components and slots for composition rather than Jinja2 template inheritance. The following Jinja2 directives are intentionally rejected at compile time with `WebComPyException` — use the Python alternative shown instead:
>
> | Rejected directives | WebComPy alternative |
> |---|---|
> | `extends`, `block`/`endblock`, `include` | Compose layout and child components with `slots` or `RouterView` |
> | `macro`/`endmacro`, `call`/`endcall`, `import`, `from` | Define a `@define_component()` function (or a helper returning `html.*` / `render_template(...)`) |
> | `set`, `with`/`endwith` | Compute local variables or `Computed` signals in Python before calling `render_template()` |
> | `filter`/`endfilter`, `do`, `debug`, `autoescape`/`endautoescape` | Transform values in Python expressions / built-in filters |
> | `trans`/`endtrans`, `pluralize` | Use `webcompy.i18n` (`use_i18n()`) and pass translated strings/signals into context |

## Next steps

- Learn how `Signal`, `Computed`, `ReactiveList`, and `use_state` work in [Reactive State](/documents/basic/reactive-state).
- Compare template directives with Python element helpers in [Elements & Events](/documents/basic/elements-and-events).
- Review props, slots, and scoped CSS in [Components](/documents/basic/components).
- Migrating existing Jinja2 templates? Check exact directive and filter differences in [Jinja2 Compatibility Notes](/documents/migration/compatibility-notes).
- Full API: [Template & Markdown API](/documents/api/template-and-markdown).
