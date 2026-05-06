## Why

WebComPy renders content inside a mount element (`#webcompy-app`), but the `<html>` root element is outside its control. This blocks features like class-based dark mode (e.g. Tailwind `darkMode: 'class'`), `lang` attribute management, and per-route `data-*` attributes. Developers currently need manual DOM scripting or external JS to mutate `<html>`, which breaks WebComPy's reactive model.

## What Changes

- Add `set_html_attr(key, value)` and `remove_html_attr(key)` methods on `AppDocumentRoot`
- Support both static strings and reactive `Computed` values for attributes
- Emit `<html>` tag attributes in SSG output via `generate_html()`
- Synchronize attribute changes to the live DOM during rendering in the browser
- Expose `set_html_attr` / `remove_html_attr` as forwarded properties on `WebComPyApp`

## Capabilities

### New Capabilities
- `html-attrs-control`: Reactive and static attribute management on the `<html>` element from WebComPy applications, for both browser and SSG environments.

### Modified Capabilities
<!-- Existing capabilities whose REQUIREMENTS are changing (not just implementation).
     Only list here if spec-level behavior changes. Each needs a delta spec file.
     Use existing spec names from openspec/specs/. Leave empty if no requirement changes. -->
<!-- None - this change only adds new forwarded properties without changing existing spec requirements -->

## Impact

- `webcompy/app/_root_component.py` — new `set_html_attr` / `remove_html_attr` methods
- `webcompy/app/_app.py` — forward new methods via properties
- `webcompy/cli/_html.py` — pass `html_attrs` into `<html>` element generation
- Tests: new unit tests for `AppDocumentRoot.html_attrs` and SSG output

## Known Issues Addressed

- Module-level DI fallback limitation remains unchanged; html attrs are per-app and stored on `AppDocumentRoot`, not in module globals.

## Non-goals

- Changing `<body>` or `<head>` attributes (head is already managed via `HeadPropsStore`)
- Supporting arbitrary `<html>` child manipulation (only attributes)
- Server-sent events or live reloading for `<html>` attribute changes
