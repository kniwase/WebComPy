# Tasks: fix-ssg-render-isolation-and-resource-transfer

## 1. Component generator registry (D1)

- [x] 1.1 In `webcompy/components/_generator.py`, rename `_unregistered_generators` to `_all_component_generators` and append every generator in `ComponentGenerator.__init__` unconditionally (even when `_try_register()` succeeds); update `_register_deferred_components()` to iterate it and any other references
- [x] 1.2 Verify `LazyComponentGenerator` still bypasses the registry (no `super().__init__()` call) and that resolved generators register exactly once per store
- [x] 1.3 Add a unit test: a component first defined/imported while a render context is active must appear in a later context's store and scoped-style output (reproduces the `DocsSidebar` miss)
- [x] 1.4 Add a unit test: two sequential render contexts emit identical `data-webcompy-cid` style sets for the same app state

## 2. Post-render head collection (D2)

- [x] 2.1 In `webcompy_server/_html.py`, move `get_head_content_html()` / `get_scoped_styles_html()` collection and the corresponding `<head>` string insertion out of `_generate_html_impl` and into `generate_html` after `await scheduler.await_pending()`; keep the existing `index.css`-anchor replacement mechanics
- [x] 2.2 Add a unit test: a component whose module imports during the current render still gets its scoped style into that page's head (dev-server first-hit scenario, no preload)
- [x] 2.3 Add a unit test: a reactive scoped style registered during async component setup appears as `data-webcompy-cid-rx` in prerendered HTML
- [x] 2.4 Regression-check title/meta/links and `data-webcompy-dynamic` theme style still render identically (existing tests must pass)

## 3. Per-context transfer state (D3)

- [x] 3.1 `webcompy_server/ports/_resource.py`: add a way to derive a fresh `ServerResourcePort` (shared `app_package_path`/`allow_list`, empty `_recorded`)
- [x] 3.2 `webcompy_server/ports/_fetch.py`: store `configure()` arguments on the instance and add a per-context clone that shares the external client but starts with an empty `_response_cache`
- [x] 3.3 `webcompy_server/_context.py`: provide the per-context clones from `ServerRenderContext._register_ports()`
- [x] 3.4 Add a unit test: render page A (loads resource `a.md`), then page B (loads `b.md`) in the same process; B's payload contains `b.md` and not `a.md`
- [x] 3.5 Add a unit test: fetch transfer entries are likewise per-context (page B's payload excludes page A's cached fetches)

## 4. SSG preload full route tree (D5)

- [x] 4.1 In `webcompy_cli/_generate.py`, replace the flattened `app.routes` preload loop with `app.router.preload_lazy_routes()` when available (fallback: current loop); confirm layout routes like `docs_app.layout.document:DocsLayout` are pre-resolved
- [x] 4.2 Update/extend `tests/test_ssg_lazy_preload.py` to cover a nested route with a lazy layout importing a styled non-route component

## 5. Full text-resource transfer mode (D4)

- [x] 5.1 Add `resource_transfer: Literal["used", "all-text"] = "used"` to `WebComPyBuildConfig` with validation in `__post_init__` (invalid values raise a clear error)
- [x] 5.2 In `webcompy_cli/_generate.py`, when mode is `"all-text"`, read every allow-listed text resource (extension allowlist: `.md`, `.markdown`, `.txt`, `.json`, `.csv`, `.yaml`, `.yml`, `.toml`, `.svg`, `.html`, `.xml`; warn above 256 KB per file / 1 MB total) and stash the map on the app for collection
- [x] 5.3 In `webcompy/hydration/_collect.py`, union the stashed full map into `payload.resources` when present (per-context recorded entries still win on conflict — same content anyway)
- [x] 5.4 Add unit tests: default mode payload excludes other pages' resources; `"all-text"` mode embeds all text resources deterministically regardless of generation order; binary allow-listed files are excluded; invalid mode raises

## 6. Resource preload API (D6)

- [ ] 6.1 Add `async def preload(self, paths) -> None` to `webcompy/ports/_resource.py` `ResourcePort` ABC with a default no-op implementation
- [ ] 6.2 Implement `BrowserResourcePort.preload()` in `webcompy/ports/_browser/_resource.py`: validate paths, skip payload-present ones, prime via `FetchPort.fetch()`; catch and log individual failures without raising
- [ ] 6.3 Add unit tests (testing-module renderer/fake ports): preload primes the fetch cache so a later `load_text` issues no fetch; server preload is a no-op; missing resource does not raise from `preload` but raises from `load_text`

## 7. docs_app enablement

- [ ] 7.1 Set `resource_transfer="all-text"` in `docs_app/webcompy_config.py`
- [ ] 7.2 In `docs_app/layout/__init__.py` (`DocsRoot`), schedule an idle non-render task after mount that calls `preload()` with all docs manifest `source` paths

## 8. E2E and integration verification

- [ ] 8.1 Add an E2E (or extend docs E2E): open an "early" documents page (e.g., Installation) with network capture and assert no `/_webcompy-resource/*` request fires when navigating to another docs page (with 7.1 enabled)
- [ ] 8.2 Add an E2E assertion: a documents page's initial HTML styles the sidebar (computed style check on `.docs-sidebar-section-toggle` / `.docs-sidebar-links a` before app boot)
- [ ] 8.3 Run `uv run python -m webcompy generate` for docs_app and confirm every generated page contains the `DocsSidebar` scoped style and identical style-tag sets across pages

## 9. Final checks

- [ ] 9.1 `uv run ruff check . && uv run ruff format --check . && uv run pyright`
- [ ] 9.2 `uv run python -m pytest tests/ --tb=short`
- [ ] 9.3 `openspec validate fix-ssg-render-isolation-and-resource-transfer --strict` and `python3 scripts/check-doc-spec-refs.py`
- [ ] 9.4 Update `AGENTS.md` File → Spec Mapping / invariant tables if any spec references changed
