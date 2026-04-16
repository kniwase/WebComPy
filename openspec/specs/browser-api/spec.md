# Browser API Abstraction

## Overview

WebComPy abstracts browser APIs behind a `browser` module that is `None` on the server and a `PyScriptBrowserModule` proxy in the browser. All DOM interaction code gates on `if browser:` checks.

## Environment Detection (`utils/_environment.py`)

- `ENVIRONMENT` is computed once at import time via `_get_environment()`
- **`"pyscript"`**: When `platform.system() == "Emscripten"` (running in PyScript/Pyodide)
- **`"other"`**: Standard Python (server-side)

## Module Loading (`_browser/_modules.py`)

- If `ENVIRONMENT == "pyscript"`: imports `browser` from `_browser._pyscript`
- Otherwise: `browser = None`

## PyScript Browser Module (`_browser/_pyscript/__init__.py`)

### _PyScriptBrowserModule

- Extends `ModuleType` to act as a dynamic module-like object
- On init, imports `pyscript`, `pyodide`, and `js` modules
- All attributes from `js` (the browser `window` object) are set as attributes on the module
- This creates a unified `browser` namespace providing:
  - `browser.pyscript`: PyScript module (for `ffi.create_proxy`, `ffi.is_none`)
  - `browser.pyodide`: Pyodide module
  - `browser.document`: DOM document
  - `browser.window`: Window object
  - `browser.fetch`: Fetch API
  - `browser.FormData`: FormData constructor
  - All other `window` properties (hundreds, typed as `Any`)

## Type Stubs (`_browser/_modules.pyi`)

- Provides type hints for the `browser` module
- `BrowserModule` Protocol with `pyscript`, `pyodide`, and hundreds of `window` properties/constructors
- `PyScriptFfi` Protocol: `create_proxy`, `is_none`, `to_js`, `assign`
- `browser: BrowserModule | None` — the key type annotation

## Usage Pattern Across Codebase

All browser-dependent code follows this pattern:

```python
from webcompy._browser._modules import browser

if browser:
    # DOM manipulation, event handling, etc.
    node = browser.document.createElement("div")
else:
    # Server-side fallback (SSG, etc.)
    raise WebComPyException("Not in Browser environment.")
```

## Design Constraints

- No fallback implementations for browser APIs when running server-side (raises exceptions instead)
- The `browser` module is a catch-all proxy — all `window` attributes are available but typed as `Any`
- `pyscript.ffi.create_proxy()` must be paired with `.destroy()` to avoid memory leaks
- `pyscript.ffi.is_none()` is used to check for JavaScript `null`/`undefined`
- Simple binary detection: server or browser, no partial availability checks