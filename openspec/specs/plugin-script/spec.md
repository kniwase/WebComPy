# Plugin Script

## Purpose

Plugin scripts provide a declarative mechanism for loading JavaScript resources in the browser at runtime, with support for conditional loading based on runtime expressions (e.g., URL query parameters). This enables patterns like "load a debug toolbar only when `?debug=True` is in the URL" without requiring developers to write raw inline JavaScript.

## Requirements

### Requirement: PluginScript shall be a typed descriptor for script loading

The framework SHALL provide a `PluginScript` dataclass with fields for HTML attributes (`attrs`), optional inline code (`script`), optional runtime condition (`condition`), and placement (`in_head`).

#### Scenario: Creating a PluginScript with only attributes
- **WHEN** a developer creates `PluginScript(attrs={"type": "text/javascript", "src": "https://example.com/lib.js"})`
- **THEN** `attrs` SHALL store the provided dict
- **AND** `script` SHALL default to `None`
- **AND** `condition` SHALL default to `None`
- **AND** `in_head` SHALL default to `False`

#### Scenario: Creating a PluginScript with inline code
- **WHEN** a developer creates `PluginScript(attrs={"type": "text/javascript"}, script="console.log('hello')")`
- **THEN** `script` SHALL store `"console.log('hello')"`
- **AND** no `src` attribute is required on `attrs`

#### Scenario: Creating a PluginScript with a condition
- **WHEN** a developer creates `PluginScript(attrs={"src": "https://example.com/lib.js"}, condition="location.search.includes('debug')")`
- **THEN** the script SHALL only be loaded when the JS expression evaluates to truthy

#### Scenario: Creating a PluginScript for head placement
- **WHEN** a developer creates `PluginScript(attrs={"src": "https://example.com/lib.js"}, in_head=True)`
- **THEN** the script SHALL be placed in `<head>` when rendered

### Requirement: PluginScript with no condition shall render as a static script tag

When a `PluginScript` has no `condition` (`condition=None`), the framework SHALL render it as a static `<script>` element in the generated HTML, identical to the behavior of `app.append_script()`.

#### Scenario: Static script rendering
- **WHEN** `generate_html()` processes a `PluginScript(attrs={"type": "text/javascript", "src": "https://example.com/lib.js"}, in_head=True)`
- **THEN** the output HTML SHALL contain `<script type="text/javascript" src="https://example.com/lib.js"></script>` in the `<head>`
- **AND** no wrapper JavaScript SHALL be generated

#### Scenario: Static inline script rendering
- **WHEN** `generate_html()` processes a `PluginScript(attrs={"type": "text/javascript"}, script="console.log('hello')")`
- **THEN** the output HTML SHALL contain `<script type="text/javascript">console.log('hello')</script>` at the end of `<body>`

### Requirement: PluginScript with a condition shall render as a self-contained wrapper script

When a `PluginScript` has a `condition`, the framework SHALL generate a wrapper `<script>` tag containing JavaScript that evaluates the condition and dynamically creates the actual `<script>` element. The wrapper tag's placement in the HTML SHALL follow `in_head`: `in_head=True` places the wrapper in `<head>`, `in_head=False` places it at the end of `<body>`. When the PluginScript has `script` but no `src` in `attrs`, the inline code SHALL execute directly inside the condition block without creating a separate `<script>` element.

#### Scenario: Conditional script rendering
- **WHEN** `generate_html()` processes a `PluginScript(attrs={"type": "text/javascript", "src": "https://example.com/eruda.min.js"}, condition="new URLSearchParams(location.search).get('debug') === 'True'")`
- **THEN** the output HTML SHALL contain a wrapper `<script>` with inline JS
- **AND** the wrapper JS SHALL check `new URLSearchParams(location.search).get('debug') === 'True'`
- **AND** the actual `<script>` element SHALL only be appended to the DOM when the condition is truthy

#### Scenario: Conditional script with inline code on load
- **WHEN** `generate_html()` processes a `PluginScript(attrs={"src": "https://example.com/debug.js"}, condition="location.hash === '#debug'", script="initDebug()")`
- **THEN** the generated wrapper JS SHALL create the `<script>` element and set `onload` to execute `initDebug()`
- **AND** `initDebug()` SHALL only execute after the external script has loaded

#### Scenario: Conditional inline-only script (no src)
- **WHEN** `generate_html()` processes a `PluginScript(attrs={}, condition="location.search.includes('debug')", script="console.log('hello')")`
- **THEN** the generated wrapper JS SHALL execute `console.log('hello')` directly inside the `if` block
- **AND** no `onload` callback or dynamic `<script>` element SHALL be created

#### Scenario: Conditional head script
- **WHEN** `generate_html()` processes a `PluginScript(attrs={"src": "https://example.com/lib.js"}, condition="true", in_head=True)`
- **THEN** the wrapper `<script>` tag SHALL be placed in `<head>`
- **AND** the wrapper JS SHALL append the dynamically created element to `document.head`

#### Scenario: Multiple conditional scripts
- **WHEN** `AppConfig.scripts` contains two `PluginScript` instances, both with conditions
- **THEN** the output HTML SHALL contain two separate wrapper `<script>` tags
- **AND** each wrapper SHALL independently evaluate its own condition

### Requirement: PluginScript shall be accessible from the public API

The `PluginScript` class SHALL be exported from `webcompy.app` so that developers can import it directly.

#### Scenario: Importing PluginScript
- **WHEN** a developer writes `from webcompy.app import PluginScript`
- **THEN** the import SHALL succeed
- **AND** `PluginScript` SHALL be the dataclass defined in `webcompy/app/_config.py`
