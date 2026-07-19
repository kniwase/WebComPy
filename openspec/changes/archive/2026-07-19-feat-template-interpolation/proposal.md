## Why

WebComPy currently requires developers to define component templates using only the Python element API (`html.DIV({...}, ...)`). Compared to other frontend frameworks that allow defining templates in HTML, this is a clear weakness — it makes simple UI structures verbose, reduces accessibility for non-Python web developers, and prevents the use of standard HTML tooling. Adding an HTML template engine that parses template strings into WebComPy's reactive Element tree bridges this gap while preserving the framework's reactivity model.

## What Changes

- Add a new `webcompy/template/` module with a public `render_template` API
- Implement HTML-to-Element-tree parsing using `html.parser.HTMLParser` (stdlib only, no external dependencies)
- Support `{{ varname }}` and `{{ a.b.c }}` variable interpolation in text content — Signal objects are passed through directly to `TextElement` for reactive updates
- Support `{{ varname }}` variable interpolation in attribute values — Signals produce reactive `Computed` values (auto-dependency-tracking), non-Signals produce static strings
- Support `@event="handler_var"` event handler binding from template context
- Support `:ref="ref_var"` DomNodeRef binding from template context
- Support `locals()` and explicit dict as variable context
- Reject `<script>`, `<style>`, and other CDATA content elements in templates for security
- Handle void elements (`<br>`, `<img>`, `<input>`, etc.), boolean attributes, and HTML comments correctly
- Apply `textwrap.dedent` to template strings for clean indented source
- Extract a shared `_holes.py` module for interpolation utilities (`HOLE_PATTERN`, `LiteralText`/`Hole` dataclasses, `split_text()`, `resolve_var()`, `resolve_holes()`) used by the parser, binder, and CSS text pipeline (Change 5)
- Cache compiled Template ASTs per template string

## Capabilities

### New Capabilities
- `template-engine`: HTML template parsing and variable interpolation that produces reactive WebComPy Element trees

### Modified Capabilities
_None — new capability, no existing spec changes_

## Known Issues Addressed
_None_

## Non-goals
- Control flow blocks (`{% if %}`, `{% for %}`) — deferred to Change 2
- File-based template loading (`Path` argument) — deferred to Change 4
- Component tag resolution (`<my-component>`) — deferred to Change 3
- Expression evaluation (`{{ x + y }}`, filters, etc.) — variable name reference only
- Template inheritance or includes
- Template cache eviction policy (size limit, LRU) — unbounded cache is acceptable for compile-time constant templates; `functools.lru_cache` integration deferred to future enhancement

## Impact

- **New package**: `packages/webcompy/src/webcompy/template/` (core package, no external dependency)
- **New files**: `__init__.py`, `_holes.py`, `_parser.py`, `_ast.py`, `_binder.py`, `_cache.py`
- **Related specs**: `elements/spec.md` (TextElement, Element, create_element — leveraged, not modified)
- **Both environments**: Works in server (SSR/SSG) and browser (PyScript) — HTMLParser is stdlib
- **No breaking changes**: Pure addition, existing Python API unchanged

## Dependencies

- **Depends on**: `refactor-element-foundations` (resolved before implementation; no direct technical dependency)
- **Required by**: Change 2 (control flow), Change 4 (file loading), Change 3 (component tags — `resolve_attr` with Computed generation for component props), Change 5 (css-text — `_holes.py` shared module), Change 6 (markdown — `render_template` / `_render_nodes` pipeline), Change 7 (markdown for-expansion — `_render_nodes` shared pipeline, `_holes.resolve_var`)
- **Recommended implementation order**: First template-engine change (0 → **1** → 2 → 3 → 4 → 5 → 6 → 7)
