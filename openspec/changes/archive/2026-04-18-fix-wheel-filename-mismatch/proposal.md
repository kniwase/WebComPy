## Why

The bundled wheel filename is derived from `_normalize_name(app_package_name)`, producing filenames like `docs-src-25.108.52740-py3-none-any.whl`. However, the HTML template hardcodes the wheel URL as `app-{version}-py3-none-any.whl`. This mismatch causes micropip to request a non-existent file, receive an HTML response (or 404), and throw `BadZipFile: File is not a zip file`. All applications whose package name is not literally `"app"` are completely broken in both dev server and static site generation modes.

## What Changes

- The wheel builder MUST produce a wheel whose filename matches the URL referenced in the generated HTML
- The HTML template, dev server, and static generator must all use a single canonical source of truth for the wheel filename
- A helper function SHALL compute the wheel filename from the app package name and version, and all consumers SHALL use it

## Capabilities

### New Capabilities

(None)

### Modified Capabilities

- `wheel-builder`: The bundled wheel filename must match the URL referenced in generated HTML. The filename derivation must be consistent and predictable.
- `cli`: The HTML template, dev server, and static generator must all reference the same wheel filename derived from the actual app package name and version.

## Impact

- `webcompy/cli/_wheel_builder.py` — add a publicly accessible `get_wheel_filename` helper; `make_webcompy_app_package` naming remains derived from app name
- `webcompy/cli/_html.py` — replace hardcoded `app-{version}` URL with dynamically computed filename
- `webcompy/cli/_server.py` — use the canonical wheel filename for the in-memory file map
- `webcompy/cli/_generate.py` — no changes needed (already uses the builder output filename directly)
- Existing spec scenario "Bundled wheel naming" already states the wheel name should be `app-{version}...` — this needs updating to reflect that the name comes from the actual app package name

## Non-goals

- Changing the dist-info directory naming convention or METADATA Name field (those are fine as-is)
- Modifying how micropip/PyScript discovers or installs wheels (their URL-based loading is correct)
- Adding support for multiple wheels (the single bundled wheel approach is the intended design)