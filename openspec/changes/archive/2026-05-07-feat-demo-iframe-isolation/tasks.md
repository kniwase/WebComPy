## 1. Create _demos directory and app.py files

- [x] 1.1 Create `docs_app/static/_demos/` directory structure with per-demo subdirectories
- [x] 1.2 Create `docs_app/static/_demos/helloworld/app.py` — self-contained HelloWorld WebComPy app
- [x] 1.3 Create `docs_app/static/_demos/fizzbuzz/app.py` — self-contained FizzBuzz WebComPy app
- [x] 1.4 Create `docs_app/static/_demos/todo/app.py` — self-contained ToDo List WebComPy app
- [x] 1.5 Create `docs_app/static/_demos/fetch_sample/app.py` — self-contained Fetch Sample WebComPy app
- [x] 1.6 Copy `docs_app/static/fetch_sample/sample.json` to `docs_app/static/_demos/fetch_sample/sample.json`
- [x] 1.7 Create `docs_app/static/_demos/matplotlib_sample/app.py` — self-contained Matplotlib Sample WebComPy app

## 2. Update docs_app global dependencies

- [x] 2.1 Update `docs_app/pyproject.toml` — change `browser` optional dependencies from `["numpy", "matplotlib"]` to `[]`
- [x] 2.2 Update `docs_app/webcompy_config.py` — remove `dependencies_from="browser"`, set `dependencies=[]` explicitly
- [x] 2.3 Regenerate `docs_app/webcompy-lock.json` to reflect zero browser dependencies

## 3. Rewrite DemoDisplay with template + srcdoc + fetch

- [ ] 3.1 Add `_DEMO_SHELL_HTML` template string with `__PACKAGES__` and `{app_name}` placeholders
- [ ] 3.2 Add `_resolve_packages()` helper that reads parent config via `querySelector` and extracts webcompy wheel + extra packages
- [ ] 3.3 Add async fetch logic: `HttpClient.get(demo_path)` → source code string
- [ ] 3.4 Build iframe srcdoc: replace placeholders, wrap source code in `<script type="py">`
- [ ] 3.5 Set iframe via `DomNodeRef` + `element.srcdoc`
- [ ] 3.6 Bind fetched source code to `SyntaxHighlighting` display

## 4. Rewrite demo page components with app_name + demo_path

- [ ] 4.1 Rewrite `docs_app/pages/demo/helloworld.py` — pass `app_name="helloworld"`, `demo_path="/_demos/helloworld/app.py"`
- [ ] 4.2 Rewrite `docs_app/pages/demo/fizzbuzz.py` — same pattern
- [ ] 4.3 Rewrite `docs_app/pages/demo/todo.py` — same pattern
- [ ] 4.4 Rewrite `docs_app/pages/demo/fetch_sample.py` — same pattern
- [ ] 4.5 Rewrite `docs_app/pages/demo/matplotlib_sample.py` — same pattern

## 5. Clean up unused files

- [x] 5.1 Remove `docs_app/templates/demo/helloworld.py` (logic moved to `_demos/helloworld/app.py`)
- [x] 5.2 Remove `docs_app/templates/demo/fizzbuzz.py`
- [x] 5.3 Remove `docs_app/templates/demo/todo.py`
- [x] 5.4 Remove `docs_app/templates/demo/fetch_sample.py`
- [x] 5.5 Remove `docs_app/templates/demo/matplotlib_sample.py`
- [x] 5.6 Remove `docs_app/static/fetch_sample/sample.json` (moved to `_demos/fetch_sample/`)
- [ ] 5.7 Remove `docs_app/static/_demos/standard.html` (no longer needed — template is in Python)
- [ ] 5.8 Remove `docs_app/static/_demos/numeric.html` (no longer needed)
- [ ] 5.9 Clean up `docs_app/dist/_demos/` stale files if they exist

## 6. Run lint, type check, and tests

- [ ] 6.1 Run `uv run ruff check .` and fix any issues
- [ ] 6.2 Run `uv run pyright` and fix any type errors
- [ ] 6.3 Run `uv run python -m pytest tests/ --tb=short` and ensure all tests pass
