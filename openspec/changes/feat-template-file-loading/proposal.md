## Why

Change 1 introduced an HTML template engine with `render_template(source: str, context)`, but `source` accepts only inline Python strings. This forces developers to embed all HTML inside Python source — large templates become unreadable, designers cannot work with HTML files directly, and standard HTML tooling (syntax highlighting, validation, formatting) cannot be used without Jinja2-specific editor extensions.

The original Change 4 proposal (`render_template` accepting `pathlib.Path` with `Path.read_text()`) was rejected during planning because:

1. **Browser (CSR) failure**: After SSR hydration, navigating to a new route in the browser re-runs component setup. `Path.read_text()` raises `WebComPyException` in the PyScript environment because the browser has no access to the server's filesystem.
2. **`load_asset` SSR failure**: The existing `webcompy.assets.load_asset` imports from `app._assets_registry`, which is generated only at wheel-build time. During SSR (in dev or prod), the server runs the user's app package from source via `importlib.import_module`, where `_assets_registry.py` does not exist. Using `load_asset` directly would break SSR.
3. **Architectural redundancy**: With the framework already providing `async def` component setup (`async-component-setup/spec.md`) and a `FetchPort` for cross-environment HTTP, an asynchronous `ResourcePort` becomes natural to introduce — letting users load resources explicitly and pass the returned text to `render_template`, while leaving room for future fetch-based lazy loading with zero changes to the template engine.

This change resolves the problem by introducing an **async-only `ResourcePort`** that the template engine (and future `css_text`, `render_markdown`) uses to load resource files. The browser fetches resources from a server endpoint, while the server reads from its source tree directly. To avoid wasting a network round-trip on hydration, the SSR pass records loaded resources and embeds them in the existing hydration payload (`__webcompy_data__`), which `BrowserResourcePort` consumes on the client before any network fetch occurs.

This design unifies all three deployment modes (live SSR, static-host SSG, PyScript-direct) around a single read model — same URL, same port, different backing store — and fully eliminates the previous dev-time restart requirement: template changes are picked up by the browser on the next page load with no rebuild.

It also supersedes the existing `load_asset` API and the `_assets_registry` infrastructure; both are removed in this change since the new port covers their behavior with a wider feature set and no `app._assets_registry` hardcode bug.

## What Changes

- Add a `ResourcePort` ABC and two async-only implementations:
  - `ServerResourcePort` (in `webcompy_server`) reads resources from the application's source tree on the server filesystem; reads are not cached so dev hot iteration works; loaded paths are recorded per `RenderContext` for embedding in the hydration payload
  - `BrowserResourcePort` (in `webcompy.ports._browser`) prefers content embedded in the hydration payload; falls back to fetching `GET {base_url}_webcompy-resource/{path}` via the existing `FetchPort` if the resource was not transferred
- Add a server endpoint `GET {base_url}_webcompy-resource/{path:path}` in `webcompy_cli` (`create_asgi_app`) that serves only allow-listed (auto-detected or explicitly declared) resources from the application package directory; path traversal is rejected via realpath containment checks
- Extend `webcompy_cli`'s `generate_static_site` to copy the same allow-listed resources to `dist/_webcompy-resource/{path}` so that SSG output deployable to a static file host serves the same URL convention
- Add auto-detection of resource files in `WebComPyBuildConfig` (default patterns: `**/*.html`, `**/*.css`, `**/*.md`, `**/*.svg`, `**/*.txt`); add `resources: list[str] | None = None` and `resource_exclude: list[str] | None = None` fields to override the defaults
- Add a `resources` field to the hydration `TransferPayload` (dictionary of package-relative path → base64-encoded bytes) and a `RESOURCE_DATA_KEY` DI key so `BrowserResourcePort` can read embedded content during hydration
- Add `webcompy/resources.py` with two public async helpers `load_text(source: str | Path) -> str` and `load_bytes(source: str | Path) -> bytes`; both accept `str` or `pathlib.Path`, convert to POSIX-form package-relative paths internally, and delegate to the DI-injected `ResourcePort`
- Export `load_text` and `load_bytes` from the `webcompy` top-level package
- **Remove** the existing `webcompy.assets.load_asset` API and `AssetNotFoundError`, the `WebComPyBuildConfig.assets` field, the `_generate_assets_registry` wheel-builder helper, and the runtime injection of `app._assets_registry` modules — all superseded by the new `ResourcePort`

## Capabilities

### New Capabilities
- `resource-port`: An async-only, injectable Port abstraction for reading application resource files (HTML, CSS, Markdown, images, fonts, …) in both server (SSR/SSG build) and browser (CSR/initial hydration) environments; the browser side prefers embedded payload content and falls back to fetching from a server endpoint

### Modified Capabilities
- `cli`: The dev/prod SSR server SHALL expose a `GET {base_url}_webcompy-resource/{path:path}` endpoint that serves allow-listed resources from the application package directory; the `generate_static_site` command SHALL copy allow-listed resources to `dist/_webcompy-resource/{path}`
- `hydration-data-transfer`: The `TransferPayload` SHALL include a `resources` field (path → base64 bytes) populated by `ServerResourcePort` during SSR and consumed by `BrowserResourcePort` during hydration, eliminating the duplicate fetch on initial page load

### Removed Capabilities
- `wheel-builder`: The `assets` parameter on `make_webcompy_app_package`, the `_generate_assets_registry` helper, and the generated `{app_name}/_assets_registry.py` modules are removed. The `WebComPyBuildConfig.assets` field is removed. The public `webcompy.assets.load_asset` / `AssetNotFoundError` APIs are removed. The resource-port ADDED spec (`specs/resource-port/spec.md`) covers only new APIs; legacy-asset removal scenarios are colocated under the wheel-builder REMOVED spec.

## Known Issues Addressed

- **Browser CSR navigation fails when `render_template` accepts `Path` arguments** — the original Change 4 design raised `WebComPyException` in the PyScript environment because the browser has no filesystem. This change sidesteps the problem entirely by keeping `render_template` `str`-only and routing resource reading through an explicit `ResourcePort` that the browser reaches via HTTP and/or the hydration payload.
- **`load_asset` hardcodes the app package name to `app`** — apps not named `app` (e.g., `docs_app`) cannot use the existing asset lookup. This change removes the hardcoded API entirely; the new port discovers the application package via DI context.
- **Resource files must be redeployed separately from Python code** — the original design left templates on disk; this change ships them through the same distribution path (SSR live server's static endpoint, or SSG's `dist/_webcompy-resource/` copy) so a single deployment artifact covers all resource access.
- **Dev-time template changes require a server restart** — the previous (wholly-wheel-based) proposal required a restart to refresh the browser's wheel copy. With the fetch-based model and an un-cached server endpoint, browser-side resource content updates immediately on the next page load after a server-side file change (subject to uvicorn reload picking up any `.py` changes that affect the build config).

## Non-goals

- **`render_template(Path)` signature change** — `render_template(source: str, ctx)` is kept as-is. Users who want file-based templates call `load_text(path)` themselves and pass the resulting string. This keeps the template engine narrowly scoped and avoids an async/sync split inside the renderer.
- **Sync `ResourcePort` interface** — only `async def load_text` / `async def load_bytes` are exposed. Sync setups that need resources must convert to `async def`. This collapses a previously considered sync/async compatibility surface into one consistent async API.
- **Wheel bundling of resource files** — resources are not bundled into the app wheel. Bundling would require either rebuild-on-change (re-introducing the dev restart problem) or duplicate storage. The endpoint + SSG copy strategy replaces wheel bundling.
- **`load_asset` compatibility shim** — the existing API is removed without a deprecation cycle. No internal consumers remain; external consumers must migrate to `load_text`/`load_bytes`.
- **Browser-side fetch result caching** — the browser port does not cache fetched content during a session. Freshness on every fetch keeps dev iteration responsive; production optimizations (ETag, content-hash headers) are deferred to a separate change.
- **Resource file watching / auto-reload** — uvicorn's reload behavior on `.html`/`.css`/`.md` files is not expanded. SSR-side reads pick up file changes immediately; browser-side reads from the live server pick them up on the next page load. Full hot-module-replacement for templates is a separate change.
- **`load_text` / `load_bytes` as composables (`use_*`)** — these are plain async helper functions, not composables, because they hold no reactive state across setup frames.

## Impact

- **New spec capability**: `resource-port`
- **New files**:
  - `packages/webcompy/src/webcompy/ports/_resource.py` — `ResourcePort` ABC + `ResourceNotFoundError`
  - `packages/webcompy/src/webcompy/ports/_browser/_resource.py` — `BrowserResourcePort`
  - `packages/webcompy-server/src/webcompy_server/ports/_resource.py` — `ServerResourcePort`
  - `packages/webcompy/src/webcompy/resources.py` — public helpers `load_text`, `load_bytes`
- **Modified files in `packages/webcompy/src/webcompy/`**:
  - `app/_render_context.py` — provide `RESOURCE_PORT_KEY` in both browser and server `_register_ports`; populate `RESOURCE_DATA_KEY` from hydration payload in browser context
  - `ports/_keys.py` — add `RESOURCE_PORT_KEY` and `RESOURCE_DATA_KEY`
  - `hydration/_payload.py` — add `resources: dict[str, str] = field(default_factory=dict)` to `TransferPayload` (base64-encoded bytes keyed by package-relative path); update `serialize_payload` / `deserialize_payload` accordingly
  - `__init__.py` — export `load_text`, `load_bytes`; remove `load_asset` and `AssetNotFoundError` exports
- **Modified files in `packages/webcompy-server/src/webcompy_server/`**:
  - `__init__.py` (`configure_server_context`) — accept a new `resource_port: ServerResourcePort | None = None` keyword and set `app._server_resource_port = resource_port` when provided (mirrors the existing `app._server_fetch_port` assignment). Existing test-helper callers that omit the kwarg keep the attribute `None`, so `inject(RESOURCE_PORT_KEY, default=None)` returns `None` cleanly
  - `_context.py` — read `app._server_resource_port` in `_register_ports`; provide it via `RESOURCE_PORT_KEY` when non-`None`; populate `RESOURCE_DATA_KEY` (empty) and ensure `RenderContext` accumulates loaded resources for the hydration payload
  - `_html.py` — no payload changes; the hydration `<script>` injection path stays as-is (payload assembly moved to `_collect.py`, see below)
  - `_collect.py` (in `packages/webcompy/src/webcompy/hydration/`) — `collect_transfer_data()` reads `inject(RESOURCE_PORT_KEY, default=None)`; when non-`None`, calls `get_recorded_resources()` and passes the base64-encoded map into `TransferPayload(resources=...)`. This is shared code used by SSR, not `_html.py`.
- **Modified files in `packages/webcompy-cli/src/webcompy_cli/`**:
  - `config/_build_config.py` — add `resources: list[str] | None = None` and `resource_exclude: list[str] | None = None`; **remove** `assets: dict[str, str] | None`
  - `_build.py` — detect resources via a new `_detect_resources(app_package_path, include, exclude)` helper; **construct** `ServerResourcePort(app_package_path, allow_list)` and pass it to `configure_server_context(app, resource_port=...)` (single owner — `create_asgi_app` does not call `configure_server_context`); also pass the allow-list to `_server.py` and `_generate.py` via `BuildArtifacts.resource_allow_list`
  - `_server.py` (`create_asgi_app`) — register the `GET {base_url}_webcompy-resource/{path:path}` route, with allowlist checks and `realpath` containment
  - `_generate.py` (`generate_static_site`) — copy allow-listed resources to `dist/_webcompy-resource/{path}` preserving relative directory layout (insertion point: after `create_asgi_app` populates `artifacts`, alongside the other asset-copy blocks)
  - `_wheel_builder.py` — **remove** `_generate_assets_registry` helper, `_assets_to_package_data` helper (dead code after `assets=` removal), and the `assets` parameter plumbing; remove `_assets_registry.py` generation
- **Removed files**:
  - `packages/webcompy/src/webcompy/assets.py` — `load_asset` and `AssetNotFoundError`
  - `tests/test_assets.py` — existing asset tests
- **Modified test files**:
  - `tests/test_wheel_builder.py` — remove the 6 references to `_generate_assets_registry` / `_assets_registry.py` (import line 9, test bodies at lines 415, 423, 448, 449, 470) — these test the removed helper
- **No breaking changes to user-visible template engine API**: `render_template(source: str, ctx)` is unchanged. The addition is `webcompy.load_text`, `webcompy.load_bytes`, and `webcompy.resources.{load_text, load_bytes}`.
- **Change 5 (`feat-template-css-text`) and Change 6 (`feat-template-markdown`)** will be updated in follow-up changes to consume `ResourcePort` instead of the originally planned `_load_file` helper; their existing artifacts (which assumed `_load_file`) become obsolete.

## Dependencies

- **Depends on**:
  - Change 1 (`feat-template-interpolation`) — the `render_template` API and `__init__.py` location
  - `async-component-setup` spec — async `def` setup function support (required for calling `load_text` / `load_bytes`)
  - `hydration-data-transfer` and `transfer-codec` specs — payload infrastructure extended with a `resources` field
  - `port-abstraction` spec — Port pattern (a new port is added)
  - `cli` spec — endpoint registration and SSG copy
- **Required by**:
  - Change 5 (`feat-template-css-text`) — `css_text(Path)` and `css_text_template(Path, ctx)` will use `ResourcePort`
  - Change 6 (`feat-template-markdown`) — `render_markdown(Path)` will use `ResourcePort`
- **Recommended implementation order**: Fourth template-engine change (0 → 1 → 2 → 3 → **4** → 5 → 6 → 7). Change 5/6 must be revised after this change to consume `ResourcePort`.
