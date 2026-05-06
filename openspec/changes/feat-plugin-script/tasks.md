## 1. Data Model

- [x] 1.1 Define `PluginScript` dataclass in `webcompy/app/_config.py` with fields: `attrs`, `script`, `condition`, `in_head`
- [x] 1.2 Add `scripts: list[PluginScript] = []` field to `AppConfig` dataclass (default `field(default_factory=list)`)
- [x] 1.3 Export `PluginScript` from `webcompy/app/__init__.py`

## 2. HTML Generation

- [x] 2.1 Add `_render_plugin_script(ps: PluginScript) -> _HtmlElement` helper in `webcompy/cli/_html.py` that converts a single `PluginScript` into either a static `<script>` element (no condition) or a wrapper `<script>` with inline JS (has condition). **The wrapper tag placement follows `in_head`: wrapper is placed in `<head>` for `in_head=True`, at end of `<body>` for `in_head=False`.**
- [x] 2.2 In `generate_html()`, extend `scripts_head` and `scripts_body` to include scripts from `app.config.scripts`. For each PluginScript, call `_render_plugin_script()` and place the result according to `in_head` flag.
- [ ] 2.3 Ensure `app.head["script"]` and `app.append_script()` continue to work identically (no regression)

## 3. Consumer: docs_app

- [x] 3.1 In `docs_app/webcompy_config.py`, add `from webcompy.app import PluginScript` and configure eruda scripts with `condition="new URLSearchParams(location.search).get('debug') === 'True'"`
- [x] 3.2 Remove the two `append_script` calls for eruda from `docs_app/bootstrap.py`

## 4. Testing

- [x] 4.1 Add unit test for `PluginScript` dataclass instantiation and defaults
- [x] 4.2 Add unit test for `generate_html()` output with conditional scripts (verify wrapper `<script>` is correctly formatted)
- [x] 4.3 Add unit test for `generate_html()` output with unconditional scripts (verify static `<script>` is unchanged)
- [x] 4.4 Add E2E test: verify eruda is NOT loaded on `/` (no query param), verify eruda IS loaded on `/?debug=True`
- [x] 4.5 Add E2E test file to CI matrix in `.github/workflows/ci.yml`
