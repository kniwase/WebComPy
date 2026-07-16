## Why

Change 1 requires template strings to be inline in Python source. For larger templates or team workflows where designers work with HTML files directly, it's essential to support loading templates from separate `.html` files. Separating templates from Python also improves readability and enables standard HTML tooling (syntax highlighting, validation) without Jinja2-specific editor extensions.

## What Changes

- Extend `render_template` to accept `pathlib.Path` as the first argument
- Load file content synchronously on the server using `Path.read_text(encoding="utf-8")`
- Reject file paths in the browser (PyScript) environment with a helpful error message pointing to inline strings
- Resolve relative paths against the calling Python module's directory
- Do NOT cache file reads (dev server should pick up template changes without restart)

## Capabilities

### New Capabilities
_None — extends `template-engine`_

### Modified Capabilities
- `template-engine`: `render_template` source argument extended to accept `str | Path`

## Known Issues Addressed
_None_

## Non-goals
- Browser file loading (future: build-time inlining)
- Template file watching/auto-reload
- Binary/encoded template loading (UTF-8 only)
- Asynchronous file loading

## Impact

- **New file**: `template/_files.py` — `_load_file` helper and `_find_caller_dir` utility (extracted to shared module to avoid circular imports with `_css_template.py` in Change 5)
- **Modified file**: `template/__init__.py` — `render_template` signature change, delegates to `_load_file` from `_files.py`
- **New behavior**: Path resolution via `inspect.stack()` for server, feature detection for browser
- **No new dependencies**: Uses stdlib `pathlib` and `inspect`
- **No breaking changes**: String-based usage unchanged

## Dependencies

- **Depends on**: Change 1 (template interpolation — `render_template` API)
- **Required by**: Change 5 (css-text — `css_text(Path)` uses `_load_file`), Change 6 (markdown — `render_markdown(Path)` uses `_load_file`)
- **Recommended implementation order**: Fourth template-engine change (0 → 1 → 2 → 3 → **4** → 5 → 6 → 7) — can be implemented at any time after Change 1
