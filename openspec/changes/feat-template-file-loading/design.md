## Context

Change 1's `render_template` accepts `source: str`. Developers must embed templates as Python strings. For production applications with complex templates, separate `.html` files are preferred — they enable HTML tooling, designer collaboration, and cleaner separation of concerns.

The main constraint is dual-environment support: server (standard Python with filesystem access) vs browser (PyScript without filesystem). The browser environment cannot use `Path.read_text()`, so file-based templates are server-only for MVP with a future build-time inlining option.

## Goals / Non-Goals

**Goals:**
- Accept `pathlib.Path` as source argument to `render_template`
- Load files synchronously on server (standard Python)
- Reject file paths in browser with helpful error message
- Resolve relative paths against caller module directory
- Skip file read caching for dev server responsiveness

**Non-Goals:**
- Browser file loading (future: build-time inlining)
- Template file watching/auto-reload
- Binary/encoded template loading (UTF-8 only)
- Asynchronous file loading

## Decisions

### D1: `str | Path` union type for source parameter

`render_template` accepts `source: str | Path`. String sources go through existing path; Path sources trigger file loading.

**Rationale**: Clean API. Single function with type-based dispatch. No need for separate `render_template_from_file` function.

### D2: `_load_file` as shared module in `_files.py`

`_load_file(path: Path) -> str` and `_find_caller_dir() -> str | None` SHALL be defined in `webcompy/template/_files.py`. This module has no imports from other template submodules (only `inspect`, `os`, `pathlib`, `webcompy`, and `webcompy.utils._environment`), making it a clean leaf module importable from `__init__.py`, `_css_template.py`, and anywhere else that needs file loading.

**Rationale**: Change 5's `_css_template.py` needs `_load_file` for `css_text(Path(...))`. If `_load_file` were in `__init__.py`, importing it from `_css_template.py` would create a circular import (`__init__.py` → `_css_template.py` → `__init__.py`). Extracting to `_files.py` (a leaf with no template-internal imports) resolves this cleanly. Change 6's `render_markdown` (also in `__init__.py`) benefits from the same extraction.

### D3: Caller-module-relative path resolution

Relative paths are resolved against the directory of the calling Python module, using `inspect.stack()` to find the caller's `__file__`.

**Frame-skipping strategy**: `inspect.stack()` returns frames starting from the innermost call. Framework-internal frames (`_load_file`, `render_template`, `render_markdown`) whose filenames are within the `webcompy` package directory SHALL be skipped. The first frame whose filename is outside the `webcompy` package SHALL be treated as the caller.

```python
import inspect
import os
import webcompy

_webcompy_root = os.path.dirname(webcompy.__file__)

def _find_caller_dir() -> str | None:
    for frame_info in inspect.stack()[2:]:  # skip _find_caller_dir itself + _load_file
        if _webcompy_root not in frame_info.filename:
            return os.path.dirname(frame_info.filename)
    return None
```

**Rationale**: Natural convention — templates placed next to their component module files. Moving the module and its templates together preserves relative paths. The frame-skipping loop handles the variable-depth indirection (e.g., `render_markdown` → `_load_file` has more frames than `render_template` → `_load_file`).

**Fallback**: If `inspect.stack()` fails or all frames belong to the framework (possible in PyScript or tooling contexts), treat the path as relative to the current working directory (`os.getcwd()`).

### D4: No file read caching

Template file contents are read on every `render_template` call. Only the parsed Template AST is cached (by content string, as in Change 1).

**Rationale**: During development, template files change frequently. Re-reading ensures dev server picks up changes without restart. In production, only one read per component setup occurs (AST cache handles subsequent calls).

### D5: Browser rejection with helpful error

When `ENVIRONMENT == "pyscript"`, file path arguments raise `WebComPyException` with a message suggesting inline strings.

**Rationale**: Clear, actionable error. Future: build-time inlining converts file references to string constants before browser deployment.

## Risks / Trade-offs

- **[Risk] `inspect.stack()` PyScript compatibility** → Mitigation: Wrapped in try/except with `os.getcwd()` fallback (see D2 frame-skipping strategy). Spike to verify before implementation.
- **[Risk] File I/O per component setup could be slow in SSG** → Mitigation: SSG renders each page once; file reads are negligible compared to network/JS loading. For large SSG sites, AST caching (by content) still applies.

## Open Questions

None — all design decisions resolved during planning phase.
