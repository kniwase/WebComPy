## 1. Data Model

- [ ] 1.1 Define `PluginScript` dataclass in `webcompy/app/_config.py` with fields: `attrs`, `script`, `condition`, `in_head`
- [ ] 1.2 Add `scripts: list[PluginScript] = []` field to `AppConfig` dataclass (default `field(default_factory=list)`)
- [ ] 1.3 Export `PluginScript` from `webcompy/app/__init__.py`

## 2. HTML Generation

- [ ] 2.1 Add `_render_plugin_script(ps: PluginScript) -> _HtmlElement` helper in `webcompy/cli/_html.py` that converts a single `PluginScript` into either a static `<script>` element (no condition) or a wrapper `<script>` with inline JS (has condition)
- [ ] 2.2 In `generate_html()`, extend `scripts_head` and `scripts_body` to include scripts from `app.config.scripts`, using `in_head` flag for placement
- [ ] 2.3 Ensure `app.head["script"]` and `app.append_script()` continue to work identically (no regression)

## 3. Consumer: docs_app

- [ ] 3.1 In `docs_app/webcompy_config.py`, add `from webcompy.app import PluginScript` and configure eruda scripts with `condition="new URLSearchParams(location.search).get('debug') === 'True'"`
- [ ] 3.2 Remove the two `append_script` calls for eruda from `docs_app/bootstrap.py`

## 4. Testing

- [ ] 4.1 Add unit test for `PluginScript` dataclass instantiation and defaults
- [ ] 4.2 Add unit test for `generate_html()` output with conditional scripts (verify wrapper `<script>` is correctly formatted)
- [ ] 4.3 Add unit test for `generate_html()` output with unconditional scripts (verify static `<script>` is unchanged)
- [ ] 4.4 Add E2E test: verify eruda is NOT loaded on `/` (no query param), verify eruda IS loaded on `/?debug=True`
- [ ] 4.5 Add E2E test file to CI matrix in `.github/workflows/ci.yml`
