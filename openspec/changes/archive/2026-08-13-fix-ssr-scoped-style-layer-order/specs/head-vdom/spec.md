# head-vdom Delta: fix-ssr-scoped-style-layer-order

## MODIFIED Requirements

### Requirement: HeadElement SHALL manage head content as VDOM children

A `HeadElement` class SHALL represent the `<head>` element as a VDOM node. The class SHALL receive a `HeadPropsStore` for reactive title and meta access. In the browser, `HeadElement._render()` SHALL inject `<style id="webcompy-scoped-styles">` and per-component `<style data-webcompy-cid="...">` elements into `document.head`. In SSG, head HTML generation SHALL be split into two methods: `HeadElement.get_head_content_html()` SHALL produce HTML strings for title, meta, the `*[hidden]` utility style, dynamic style, and link elements; `HeadElement.get_scoped_styles_html()` SHALL produce HTML strings for per-component scoped style elements (`<style data-webcompy-cid="...">` and `<style data-webcompy-cid-rx="...">`). The split allows the SSG assembler to emit scoped styles after the framework stylesheet link that declares the cascade layer order (see `openspec/specs/css-architecture/spec.md`).

#### Scenario: Initial head rendering in browser
- **WHEN** a `HeadElement` is first rendered in browser environment
- **THEN** it SHALL inject a `<style id="webcompy-scoped-styles">` element with `*[hidden]{display:none}` into `document.head`
- **AND** it SHALL inject `<style data-webcompy-cid="...">` elements for each registered component with scoped CSS
- **AND** it SHALL NOT duplicate elements that already exist from SSR

#### Scenario: SSG head rendering
- **WHEN** `generate_html()` renders a page during SSG
- **THEN** `HeadElement.get_head_content_html()` SHALL produce the inner `<head>` HTML string content for `<title>`, `<meta>`, the `*[hidden]` utility `<style>`, dynamic `<style>`, and `<link>` elements as appropriate
- **AND** `HeadElement.get_scoped_styles_html()` SHALL produce the per-component scoped `<style>` elements
- **AND** `<base>`, framework stylesheet `<link>` elements, core `<link>`, `<script>` (pyscript), plugin scripts, and the final placement of scoped styles SHALL remain the responsibility of `_html.py`
- **AND** the SSG code SHALL NOT need to manually construct title, meta, style, or app link HTML fragments

#### Scenario: Reactive title update in browser
- **WHEN** a component calls `context.set_title("New Title")`
- **THEN** the `HeadPropsStore.title` reactive value SHALL update
- **AND** `HeadElement` SHALL detect the change during re-render
- **AND** `document.title` SHALL be updated accordingly
