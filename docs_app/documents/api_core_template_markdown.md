---
title: Template & Markdown API
description: API reference for webcompy.template including HTML template rendering, AST nodes, CSS helpers, and Markdown parsing.
---

# Template & Markdown API

<!-- author:start:intro -->
API reference for `webcompy.template`: template rendering, expressions and directive AST nodes, CSS block helpers, and Markdown document loading/parsing.
<!-- author:end:intro -->

<!-- generated:start -->

## Template Rendering & AST

### AttrSpec

```python
class AttrSpec:
    name: str
    value: list[LiteralText | Hole] = field(default_factory=list)
    is_boolean: bool = False
```

Key: `webcompy.template._ast:AttrSpec` · Exports: `from webcompy.template import AttrSpec`

A parsed attribute on a template element.

**Args:**

- `name`: Attribute name, including directive prefixes such as `@` (event handlers) and `:` (ref/bind).
- `value`: Interpolated value parts, empty for boolean attributes.
- `is_boolean`: Whether the attribute was written without a value.

**Attributes:**

- `name`: Attribute name, including directive prefixes.
- `value`: Interpolated value parts.
- `is_boolean`: Whether the attribute was written without a value.

### bind_children

```python
def bind_children(nodes: list[TemplateNode], ctx: dict[str, Any]) -> list[ElementChildren]
```

Key: `webcompy.template._binder:bind_children` · Exports: `from webcompy.template import bind_children`

Bind template nodes into concrete child elements using `ctx`.

Dispatches on node kind: text nodes interpolate holes into strings, `SignalBase` values, or `ElementAbstract` children; element nodes resolve to `Element` instances or component generators; `if` nodes evaluate branches (reactively via a `SwitchElement` when signals are involved); `for` nodes expand the iterable (reactively via `repeat` when it is a signal).

**Args:**

- `nodes`: Parsed template nodes to bind.
- `ctx`: Template context mapping variable names to values.

**Returns:** Children ready for element constructors, mixing `ElementAbstract` instances, strings, and signals.

### format_value

```python
def format_value(value: Any) -> str
```

Key: `webcompy.template._holes:format_value` · Exports: `from webcompy.template import format_value`

Shared formatter for `{{ }}` hole interpolation results.

Used by three consumers that must agree on edge-case rendering:

* `resolve_holes` for CSS text (via `css_text_template`)
* `resolve_attr` for static attribute values
* `resolve_attr` for reactive attribute `Computed` closures

Rules:

* `None` → empty string (prevents `str(None) == "None"` leaking
  into CSS / attribute output)
* `SignalBase` whose `.value` is `None` → empty string
* `SignalBase` whose `.value` is a string → `.value`
* `SignalBase` whose `.value` is anything else → `str(value)`
* anything else → `str(value)`

**Args:**

- `value`: Interpolated value to format.

**Returns:** The formatted string representation, or an empty string for `None` and for signals holding `None`.

### get_or_compile

```python
def get_or_compile(
    source: str,
    parse_fn: Callable[[str], list[TemplateNode]] | None = None,
) -> list[TemplateNode]
```

Key: `webcompy.template._cache:get_or_compile` · Exports: `from webcompy.template import get_or_compile`

Return parsed nodes for `source`, compiling on a cache miss.

Sources are dedented and stripped before cache lookup, and entries are keyed by both the normalized source and the parse function. The cache holds at most `_TEMPLATE_CACHE_MAX_SIZE` entries, evicting the least recently used entry on overflow.

**Args:**

- `source`: Template source text.
- `parse_fn`: Optional custom parser; defaults to `parse_template`.

**Returns:** Parsed template nodes for the source.

### Hole

```python
class Hole:
    expr_source: str
    plan: ExpressionPlan
```

Key: `webcompy.template._holes:Hole` · Exports: `from webcompy.template import Hole`

An interpolation hole (`{{ ... }}`) found in template text.

**Args:**

- `expr_source`: Raw expression source between the braces.
- `plan`: Compiled expression plan used for evaluation.

**Attributes:**

- `expr_source`: Raw expression source between the braces.
- `plan`: Compiled expression plan used for evaluation.

### LiteralText

```python
class LiteralText:
    text: str
```

Key: `webcompy.template._holes:LiteralText` · Exports: `from webcompy.template import LiteralText`

A static text part adjacent to interpolation holes.

**Args:**

- `text`: Static text content.

**Attributes:**

- `text`: Static text content.

### render_markdown

```python
def render_markdown(
    source: str,
    context: Mapping[str, Any] | None = None,
    *,
    heading_ids: bool = False,
    code_blocks: bool = False,
    classes: Mapping[str, str] | None = None,
) -> ElementAbstract
```

Key: `webcompy.template:render_markdown` · Exports: `from webcompy.template import render_markdown`

Render a Markdown source string into WebComPy elements.

The source is split into plain segments and `{% for %}` directive blocks; plain segments are rendered through the injected `MarkdownPort` and bound against `context` like templates, while directive blocks expand into reactive loops. Optional post-processing adds slug ids to headings, replaces fenced code blocks with `CodeBlock` components, or applies a tag-to-class mapping. A single resulting element is returned as-is; multiple roots are wrapped in a fragment.

**Args:**

- `source`: Markdown source text; common leading indentation is stripped from multi-line sources.
- `context`: Template context used for variable interpolation inside the Markdown.
- `heading_ids`: When `True`, add deduplicated slug ids to headings.
- `code_blocks`: When `True`, replace fenced code blocks with `CodeBlock` components.
- `classes`: Mapping of HTML tag names to CSS classes applied to the matching rendered elements.

**Returns:** The rendered element, or a fragment when rendering produced multiple roots.

### render_template

```python
def render_template(source: str, context: Mapping[str, Any] | None = None) -> Element
```

Key: `webcompy.template:render_template` · Exports: `from webcompy.template import render_template`

Compile an HTML template source into a single reactive element.

The source is parsed and bound against `context`; interpolation holes, control-flow directives, and component tags resolve the same way as in component templates.

**Args:**

- `source`: HTML template source with exactly one root element.
- `context`: Template context used for variable interpolation.

**Returns:** The bound root element.

**Raises:**

- `WebComPyException`: When the rendered source does not have exactly one root element.

### resolve_holes

```python
def resolve_holes(text: str, ctx: dict[str, Any]) -> str
```

Key: `webcompy.template._holes:resolve_holes` · Exports: `from webcompy.template import resolve_holes`

Interpolate `{{ }}` holes in `text` with values from `ctx`.

**Args:**

- `text`: Template text containing optional holes.
- `ctx`: Template context mapping variable names to values.

**Returns:** The rendered string with holes replaced by formatted values.

### resolve_tag

```python
def resolve_tag(tag: str, store: ComponentStore) -> tuple[TagResolution, str | None]
```

Key: `webcompy.template._naming:resolve_tag` · Exports: `from webcompy.template import resolve_tag`

Resolve a parsed tag name to either NEWLINE / HTML / COMPONENT.

Returns `(TagResolution, component_name_or_None)`. `component_name` is the registered name in `ComponentStore` when resolution is COMPONENT; for the other outcomes it is `None`.

Resolution rules:

* `"br"` → NEWLINE (special-cased to skip ComponentStore lookup).
* Tag containing at least one hyphen → kebab-to-Pascal conversion, then
  ComponentStore lookup. A missing match raises `WebComPyException`
  because the user explicitly used a hyphenated component-like tag.
* Tag with no hyphen → ComponentStore lookup using the tag name as-is.
  A missing match falls back to HTML element (lenient, since the tag is
  ambiguous and could be a future HTML custom element).

**Args:**

- `tag`: Parsed tag name.
- `store`: Component registry used for COMPONENT resolution.

**Returns:** Pair of the resolution kind and the registered component name when the resolution is COMPONENT, otherwise `None`.

**Raises:**

- `WebComPyException`: If a hyphenated tag does not match any registered component.

### resolve_var

```python
def resolve_var(path: str, ctx: dict[str, Any]) -> Any
```

Key: `webcompy.template._holes:resolve_var` · Exports: `from webcompy.template import resolve_var`

Resolve a dotted path against `ctx`.

Traverses the path segment by segment. When a signal is encountered on an intermediate segment, returns an owned `Computed` that re-resolves from that point, so updates to the signal propagate reactively.

**Args:**

- `path`: Dotted attribute path.
- `ctx`: Template context mapping variable names to values.

**Returns:** The resolved value, or an owned `Computed` when the path crosses a signal.

### split_text

```python
def split_text(text: str, *, strict: bool = False) -> list[LiteralText | Hole]
```

Key: `webcompy.template._holes:split_text` · Exports: `from webcompy.template import split_text`

Split template text into literal parts and `{{ }}` holes.

In non-strict mode, unbalanced or malformed hole candidates are kept as literal text. In strict mode they raise instead, guaranteeing that no `{{ }}` sequence survives into the output.

**Args:**

- `text`: Template text to split.
- `strict`: Whether malformed or unclosed holes raise an error instead of being treated as literal text.

**Returns:** Interleaved `LiteralText` and `Hole` parts. Text without any hole yields a single `LiteralText`; empty input yields an empty list.

**Raises:**

- `WebComPyException`: If `strict` is True and a hole is unbalanced, contains an invalid expression, or is left unclosed.

### TagResolution

```python
class TagResolution(Enum)
```

Key: `webcompy.template._naming:TagResolution` · Exports: `from webcompy.template import TagResolution`

Outcome of resolving a parsed tag name.

**Attributes:**

- `NEWLINE`: Tag is `<br>`; renders as a newline element.
- `HTML`: Tag names a built-in HTML element.
- `COMPONENT`: Tag names a registered component.

### TemplateElement

```python
class TemplateElement:
    tag_name: str
    attrs: list[AttrSpec] = field(default_factory=list)
    children: list[TemplateNode] = field(default_factory=list)
```

Key: `webcompy.template._ast:TemplateElement` · Exports: `from webcompy.template import TemplateElement`

An element node with attributes and children.

**Args:**

- `tag_name`: Lower-case tag name.
- `attrs`: Parsed attribute specs.
- `children`: Child nodes in source order.

**Attributes:**

- `tag_name`: Lower-case tag name.
- `attrs`: Parsed attribute specs.
- `children`: Child nodes in source order.

### TemplateNode

```python
TemplateNode = TemplateText | TemplateElement | IfNode | ForNode
```

Key: `webcompy.template._ast:TemplateNode` · Exports: `from webcompy.template import TemplateNode`

Union of all node types that may appear in a parsed template tree.

### TemplateText

```python
class TemplateText:
    parts: list[LiteralText | Hole] = field(default_factory=list)
```

Key: `webcompy.template._ast:TemplateText` · Exports: `from webcompy.template import TemplateText`

A text node holding literal text and interpolation-style holes.

**Args:**

- `parts`: Interleaved `LiteralText` and `Hole` parts making up the text content.

**Attributes:**

- `parts`: Interleaved `LiteralText` and `Hole` parts making up the text content.

## CSS Helpers

### css_text

```python
def css_text(source: str) -> dict[str, StyleDict]
```

Key: `webcompy.template._css_template:css_text` · Exports: `from webcompy.template import css_text`

Convert a CSS text string into a selector-keyed `dict[str, StyleDict]`.

The returned dict matches the parameter type of `ComponentGenerator.scoped_style`, so it can be assigned directly:

```python
MyComp.scoped_style = css_text(".btn { color: red; }")
```

For file-based CSS, compose with `await load_text(path)` inside an async component setup:

```python
@define_component()
async def CardPanel(ctx):
    css_src = await load_text("styles/card.css")
    CardPanel.scoped_style = css_text(css_src)
    return html.DIV(...)
```

See `parse_css` for parsing details and limitations.

**Args:**

- `source`: CSS source string.

**Returns:** Selector-keyed dict whose values are `StyleDict` blocks.

### css_text_template

```python
def css_text_template(
    source: str,
    context: dict[str, Any],
) -> Callable[[], dict[str, StyleDict]]
```

Key: `webcompy.template._css_template:css_text_template` · Exports: `from webcompy.template import css_text_template`

Create a reactive CSS text factory supporting `{{ }}` interpolation.

The returned factory resolves `{{ varname }}` / `{{ a.b.c }}` holes from `context` (via `resolve_holes`), then parses the resolved CSS text. It is a plain synchronous `Callable[[], dict[str, StyleDict]]` suitable for `reactive_scoped_style`:

```python
color = Signal("blue")
context.use_reactive_scoped_style(
    reactive_scoped_style(
        css_text_template(".btn { color: {{ c }}; }", {"c": color})
    )
)
```

The factory MUST NOT create its own `Computed`. Dependency tracking is delegated to `ReactiveScopedStyle`, which wraps the factory in a `Computed`; `resolve_holes` reads `Signal.value` inside that closure, establishing the reactive graph.

Because the factory is synchronous, file loading MUST happen outside it (`await load_text(path)` in an async component setup before calling `css_text_template`).

**Args:**

- `source`: CSS source string with optional `{{ }}` holes.
- `context`: Mapping of variable names to values (strings, Signals, dataclasses, etc.). `Signal.value` is read at factory call time.

**Returns:** A factory that resolves holes and parses CSS on each call.

## Markdown Documents

### HeadingInfo

```python
class HeadingInfo:
    level: int
    text: str
    id: str
```

Key: `webcompy.template._markdown_document:HeadingInfo` · Exports: `from webcompy.template import HeadingInfo`

A heading entry extracted from a rendered Markdown document.

`level` is the heading depth (1-6), `text` is the resolved heading text with interpolated values, and `id` is the slug id injected into the corresponding heading element.

**Attributes:**

- `level`: Heading depth (1-6).
- `text`: Resolved heading text with interpolated values.
- `id`: Slug id injected into the corresponding heading element.

### load_markdown_document

```python
async def load_markdown_document(
    source: str | Path,
    *,
    heading_ids: bool = True,
    code_blocks: bool = True,
    classes: Mapping[str, str] | None = None,
    wrap_tables: bool = True,
    context: Mapping[str, Any] | None = None,
) -> MarkdownDocument
```

Key: `webcompy.template._markdown_document:load_markdown_document` · Exports: `from webcompy.template import load_markdown_document`

Load a Markdown file into a rendered document with TOC metadata.

Reads the source text, splits off frontmatter, renders the body through `render_markdown`, applies document transforms, and collects heading information for tables of contents.

**Args:**

- `source`: Resource path or file path of the Markdown source.
- `heading_ids`: Whether heading elements receive slug `id` attributes.
- `code_blocks`: Whether fenced code blocks are replaced with `CodeBlock` components.
- `classes`: Optional mapping from tag name to CSS class applied to matching elements.
- `wrap_tables`: Whether `<table>` elements are wrapped in `<div class="prose-table-wrapper">` for horizontal scrolling.
- `context`: Optional template context for `{{ }}` interpolation inside the Markdown body.

**Returns:** The rendered document with frontmatter metadata and heading list.

### MarkdownDocument

```python
class MarkdownDocument:
    content: ElementAbstract
    metadata: Mapping[str, Any]
    toc: tuple[HeadingInfo, ...]
```

Key: `webcompy.template._markdown_document:MarkdownDocument` · Exports: `from webcompy.template import MarkdownDocument`

A loaded Markdown document: rendered content, frontmatter, and TOC.

**Attributes:**

- `content`: Rendered element tree of the Markdown body.
- `metadata`: Frontmatter key-to-value mapping.
- `toc`: Heading entries extracted from the rendered document.

<!-- generated:end -->

## Next steps

<!-- author:start:see-also -->
- Core guides: [HTML Templates](/documents/basic/template-html), [Markdown Documents](/documents/basic/markdown-documents), and [Styling & Themes](/documents/basic/styling-and-themes).
- Deep dive: [Styling Deep Dive](/documents/advanced/styling-deep-dive).
- Related reference: [Reactivity API](/documents/api/reactivity).
<!-- author:end:see-also -->
