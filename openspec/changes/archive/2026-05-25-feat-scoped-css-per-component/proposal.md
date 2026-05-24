## Why

SSG-generated pages have a scoped CSS bug: when a user lands on a non-Home page first, then navigates to the Home page via client-side routing, the Home component's scoped CSS is missing. This happens because (1) each SSG page's HTML only includes scoped CSS for components rendered on that specific route (per-ComponentStore isolation per app instance), and (2) the browser's `<style id="webcompy-scoped-styles">` is injected once at initial render and never updated for lazy-loaded components resolved during SPA navigation. The fix requires both SSG-side completeness and browser-side incremental injection.

Additionally, head element management (title, meta, links, scripts, styles) is currently done imperatively through `AppDocumentRoot` methods. This creates a split between SSG (which reads these properties and generates HTML fragments) and browser runtime (which manipulates the DOM directly). A unified VDOM approach would eliminate this split, make head elements reactive, and provide a foundation for scoped CSS management.

**Merge context:** The `feat/scoped-css-per-component` branch was developed in parallel with `feat/testing-module` (#171), which was merged to `main` during development. The testing module introduces `TestRenderer`, `FakeBrowserDOMPort`, and scope helpers for browserless component testing. This merge must preserve both sets of changes and leverage the testing module to add HeadElement/scoped-CSS tests.

## What Changes

- **BREAKING**: Replace `AppDocumentRoot.style` (concatenated CSS string) with `AppDocumentRoot.scoped_styles` (dict of `cid -> CSS string`). The monolithic `<style id="webcompy-scoped-styles">` is replaced with per-component `<style data-webcompy-cid="...">` elements.
- Introduce `_reconcile_scoped_styles()` in `AppDocumentRoot._render()` → later moved to `HeadElement._render()` — scans ComponentStore, injects missing `<style>` elements into `<head>`, idempotent via `data-webcompy-cid` unique key.
- Pre-resolve all lazy routes during SSG so every generated page includes scoped CSS for all components.
- Introduce `HeadElement` VDOM class for declarative head management (title, meta, link, script, style, html_attrs). Replace and deprecate imperative methods on `AppDocumentRoot`.
- Update SSG `_html.py` to generate `<style>` elements from `app.scoped_styles` dict.
- **Merge**: Rebase or merge `origin/main` (#171 testing module) into this branch.
- **FakeBrowserDOMPort extension**: Extend `FakeBrowserDOMPort` to extend `ServerDOMPort` with an internal document tree, enabling `query_selector` and `get_element_by_id` to find injected elements. This allows testing HeadElement's browser-path style reconciliation in unit tests.
- **New tests**: SSG integration tests via `create_test_asgi_app` + `httpx`, and HeadElement browser-path tests via `TestRenderer` with extended `FakeBrowserDOMPort`.

## Capabilities

### New Capabilities
- `scoped-css-incremental`: Per-component `<style data-webcompy-cid="...">` management with idempotent incremental injection at browser runtime and complete collection during SSG.
- `head-vdom`: Declarative, reactive head element management via VDOM, replacing imperative `AppDocumentRoot` head methods.

### Modified Capabilities
- `testing-module`: `FakeBrowserDOMPort` SHALL extend `ServerDOMPort` instead of directly implementing `DOMPort`. It SHALL maintain an internal document tree with `<html>`, `<head>`, and `<body>` nodes, and SHALL implement `query_selector()` and `get_element_by_id()` by searching this tree. The existing `render_html()` method from `ServerDOMPort` SHALL be inherited.
- `components`: The runtime scoped CSS injection requirement SHALL change from a single monolithic `<style id="webcompy-scoped-styles">` to per-component `<style data-webcompy-cid="...">` elements. The SSR duplicate-check SHALL change from checking `getElementById("webcompy-scoped-styles")` to checking `querySelector('style[data-webcompy-cid="..."]')` per component.
- `architecture`: Head management SHALL move from imperative `AppDocumentRoot` methods to reactive VDOM via `HeadElement`, eliminating the SSG/browser head rendering split.

## Impact

- Affected code: `webcompy/app/_root_component.py`, `webcompy/app/_app.py`, `webcompy/components/_generator.py`, `webcompy/cli/_html.py`, `webcompy/cli/_generate.py`, `webcompy/elements/_head.py`, `webcompy/elements/__init__.py`, `webcompy/router/_lazy.py`, `webcompy/testing/_ports.py`, `webcompy/testing/_renderer.py`
- Affected specs: `scoped-css-incremental` (new), `head-vdom` (new), `components` (modified), `app` (modified), `app-lifecycle` (modified), `architecture` (modified), `testing-module` (modified)
- Test updates: All tests referencing `style` property, new HeadElement/scoped CSS tests using testing module
