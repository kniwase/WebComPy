## 1. File Loading Module (_files.py)

- [ ] 1.1 Create `webcompy/template/_files.py` — leaf module with no imports from other template submodules
- [ ] 1.2 Implement `_find_caller_dir() -> str | None`: use `inspect.stack()` with frame-skipping (skip frames inside `webcompy` package), return first non-framework caller's directory
- [ ] 1.3 Implement `_load_file(path: Path) -> str`: check `ENVIRONMENT`, raise `WebComPyException` for PyScript with helpful message, resolve relative path via `_find_caller_dir()`, read with `Path.read_text(encoding="utf-8")`
- [ ] 1.4 Add fallback path resolution when `inspect.stack()` fails (use `os.getcwd()`)

## 2. Public API Integration

- [ ] 2.1 Update `render_template` signature in `template/__init__.py` to `source: str | Path`; import `_load_file` from `_files.py` and dispatch based on `isinstance(source, Path)`
- [ ] 2.2 Ensure string-based usage unchanged (no regression)

## 3. Unit Tests

- [ ] 3.1 Test file loading with valid Path (server environment, tempfile)
- [ ] 3.2 Test file loading with relative Path → caller-module resolution
- [ ] 3.3 Test file loading with absolute Path
- [ ] 3.4 Test browser environment rejection (mock `ENVIRONMENT == "pyscript"`)
- [ ] 3.5 Test inline string source still works (no regression)
- [ ] 3.6 Test file content change between calls (non-cached reads)

## 4. Spike

- [ ] 4.1 Verify `inspect.stack()` functionality in PyScript environment; document fallback behavior
