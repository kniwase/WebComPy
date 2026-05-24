## Why

SSG-generated pages have a scoped CSS bug: when a user lands on a non-Home page first, then navigates to the Home page via client-side routing, the Home component's scoped CSS is missing. This happens because (1) each SSG page's HTML only includes scoped CSS for components rendered on that specific route (per-ComponentStore isolation per app instance), and (2) the browser's `<style id="webcompy-scoped-styles">` is injected once at initial render and never updated for lazy-loaded components resolved during SPA navigation. The fix requires both SSG-side completeness and browser-side incremental injection.

Additionally, head element management (title, meta, links, scripts, styles) is currently done imperatively through `AppDocumentRoot` methods. This creates a split between SSG (which reads these properties and generates HTML fragments) and browser runtime (which manipulates the DOM directly). A unified VDOM approach would eliminate this split, make head elements reactive, and provide a foundation for scoped CSS management.

## What Changes

- **BREAKING**: Replace `AppDocumentRoot.style` (concatenated CSS string) with `AppDocumentRoot.scoped_styles` (dict of `cid -> CSS string`). The monolithic `<style id="webcompy-scoped-styles">` is replaced with per-component `<style data-webcompy-cid="...">` elements.
- Introduce `_reconcile_scoped_styles()` in `AppDocumentRoot._render()` — scans ComponentStore, injects missing `<style>` elements into `<head>`, idempotent via `data-webcompy-cid` unique key.
- Pre-resolve all lazy routes during SSG so every generated page includes scoped CSS for all components.
- Introduce `HeadElement` VDOM class for declarative, reactive head management (title, meta, link, script, style). Replace imperative `set_title`/`set_meta`/`append_link`/`append_script`/`set_head` on `AppDocumentRoot`.
- Update SSG `_html.py` to generate `<style>` elements from `app.scoped_styles` dict, and render head content from `HeadElement` VDOM tree.

## Capabilities

### New Capabilities
- `scoped-css-incremental`: Per-component `<style data-webcompy-cid="...">` management with idempotent incremental injection at browser runtime and complete collection during SSG.
- `head-vdom`: Declarative, reactive head element management via VDOM, replacing imperative `AppDocumentRoot` head methods.

### Modified Capabilities
- `components`: The runtime scoped CSS injection requirement SHALL change from a single monolithic `<style id="webcompy-scoped-styles">` to per-component `<style data-webcompy-cid="...">` elements. The SSR duplicate-check SHALL change from checking `getElementById("webcompy-scoped-styles")` to checking `querySelector('style[data-webcompy-cid="..."]')` per component.
- `architecture`: Head management SHALL move from imperative `AppDocumentRoot` methods to reactive VDOM via `HeadElement`, eliminating the SSG/browser head rendering split.

## Impact

- Affected code: `webcompy/app/_root_component.py`, `webcompy/components/_generator.py`, `webcompy/cli/_html.py`, `webcompy/cli/_generate.py`, `webcompy/elements/` (new `HeadElement`)
- Affected APIs: `AppDocumentRoot.style` (removed), `AppDocumentRoot.set_title/set_meta/append_link/append_script/set_head` (deprecated, replaced by HeadElement)
- Test updates: All tests referencing `style` property or scoped CSS injection behavior
- docs_app: No changes needed (consumer code uses `app.set_head()` which remains via delegation)
