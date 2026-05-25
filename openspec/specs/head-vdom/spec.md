# Head VDOM

## Purpose

WebComPy's document head management shall use a VDOM (Virtual DOM) approach instead of imperative `AppDocumentRoot` methods. A `HeadElement` VDOM class shall manage the `<head>` element's children declaratively, providing uniform rendering for both SSG (HTML string generation) and browser runtime (DOM manipulation). This replaces the split where SSG code manually constructs HTML fragments from head properties while browser code imperatively modifies the DOM.

## Requirements

### Requirement: HeadElement SHALL manage head content as VDOM children

A `HeadElement` class SHALL represent the `<head>` element as a VDOM node. The class SHALL receive a `HeadPropsStore` for reactive title and meta access. In the browser, `HeadElement._render()` SHALL inject `<style id="webcompy-scoped-styles">` and per-component `<style data-webcompy-cid="...">` elements into `document.head`. In SSG, `HeadElement.get_head_content_html()` SHALL produce HTML strings for title, meta, scoped style, and link elements.

#### Scenario: Initial head rendering in browser
- **WHEN** a `HeadElement` is first rendered in browser environment
- **THEN** it SHALL inject a `<style id="webcompy-scoped-styles">` element with `*[hidden]{display:none}` into `document.head`
- **AND** it SHALL inject `<style data-webcompy-cid="...">` elements for each registered component with scoped CSS
- **AND** it SHALL NOT duplicate elements that already exist from SSR

#### Scenario: SSG head rendering
- **WHEN** `generate_html()` renders a page during SSG
- **THEN** `HeadElement.get_head_content_html()` SHALL produce the inner `<head>` HTML string content
- **AND** the output SHALL include `<title>`, `<meta>`, `<style>` (hidden rule + per-component scoped), and `<link>` elements as appropriate
- **AND** `<base>`, core `<link>`, `<script>` (pyscript), and plugin scripts SHALL remain the responsibility of `_html.py`
- **AND** the SSG code SHALL NOT need to manually construct title, meta, style, or app link HTML fragments

#### Scenario: Reactive title update in browser
- **WHEN** a component calls `context.set_title("New Title")`
- **THEN** the `HeadPropsStore.title` reactive value SHALL update
- **AND** `HeadElement` SHALL detect the change during re-render
- **AND** `document.title` SHALL be updated accordingly

### Requirement: HeadElement SHALL replace imperative head methods on AppDocumentRoot

`AppDocumentRoot` SHALL delegate head management to `HeadElement`. The imperative methods `set_title`, `set_meta`, `append_link`, `append_script`, `set_head`, `update_head` on `AppDocumentRoot` SHALL be replaced with `HeadElement`-based equivalents.

#### Scenario: Setting head via app
- **WHEN** a developer calls `app.set_head({"title": "My App", "meta": {...}, "link": [...]})`
- **THEN** the head configuration SHALL be passed to `HeadElement`
- **AND** subsequent rendering SHALL reflect the configured head content

#### Scenario: Appending a link
- **WHEN** a developer calls `app.append_link({"rel": "stylesheet", "href": "..."})`
- **THEN** the link SHALL be added to `HeadElement`'s children
- **AND** on next render, the link element SHALL appear in the DOM (browser) or HTML output (SSG)

### Requirement: Scoped CSS style elements SHALL be children of HeadElement

Per-component `<style data-webcompy-cid="...">` elements SHALL be managed as children of `HeadElement`, rather than being injected imperatively. `_reconcile_scoped_styles()` SHALL be integrated into `HeadElement`'s render lifecycle.

#### Scenario: HeadElement manages scoped styles
- **WHEN** a new component is registered in `ComponentStore`
- **AND** `HeadElement` renders
- **THEN** any missing `<style data-webcompy-cid="...">` elements SHALL be added
- **AND** existing elements SHALL NOT be duplicated

### Requirement: HeadElement SHALL handle plugin-provided head content

Plugin `WebComPyPlugin` instances that contribute head scripts or styles SHALL be represented as children of `HeadElement`.

#### Scenario: Plugin head scripts
- **WHEN** a plugin contributes a script via `plugin_scripts`
- **THEN** the script SHALL be included as a `<script>` child of `HeadElement`
- **AND** it SHALL appear in both SSG output and browser DOM

### Requirement: HeadElement SHALL support html_attrs management

`AppDocumentRoot` currently provides `set_html_attr`/`remove_html_attr`/`html_attrs` for managing `<html>` element attributes. This SHALL be integrated into `HeadElement` as html-level attribute management, since `<html>` is the sibling container for `<head>`.

#### Scenario: Setting html lang attribute
- **WHEN** a developer sets `app.set_html_attr("lang", "ja")`
- **THEN** the `<html>` element SHALL have `lang="ja"` in both SSG output and browser DOM

### Requirement: HeadElement SHALL support testing via FakeBrowserDOMPort

HeadElement's browser-path `_render()` method SHALL be testable without a real browser by using `FakeBrowserDOMPort` with an internal document tree. The extended `FakeBrowserDOMPort` SHALL support `query_selector("head")` returning a `FakeDOMNode`, enabling HeadElement to append `<style>` elements as children of the head node.

#### Scenario: Testing HeadElement browser path with FakeBrowserDOMPort
- **WHEN** a test creates a `FakeBrowserDOMPort` with internal document tree
- **AND** registers it in a DI scope
- **AND** registers component generators with `scoped_style` in `ComponentStore`
- **AND** calls `HeadElement._render()` within the scope
- **THEN** the internal `_head` node SHALL contain `<style id="webcompy-scoped-styles">*[hidden]{display:none}</style>`
- **AND** SHALL contain `<style data-webcompy-cid="...">` for each component with scoped CSS

#### Scenario: Idempotent HeadElement rendering via FakeBrowserDOMPort
- **WHEN** `HeadElement._render()` is called a second time with the same scope
- **THEN** no duplicate `<style>` elements SHALL be added to the internal head node
- **AND** the count of `<style>` children SHALL remain unchanged
