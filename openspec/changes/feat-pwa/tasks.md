# Tasks: feat-pwa

## 1. Configuration

- [x] 1.1 Add `ManifestConfig` and `PWAConfig` dataclasses to the webcompy-cli build config (`enabled`, manifest fields, `precache` mode (`"auto"` / `"none"`), `precache_runtime`, runtime rules list (pattern/strategy/max-entries/max-age), offline fallback path); defaults keep PWA off; wire into `WebComPyBuildConfig`
- [x] 1.2 Validate config combinations at build start (unknown strategy names, invalid patterns, fallback path existence, `precache="none"` combined with `precache_runtime`) with actionable errors

## 2. Manifest pipeline

- [x] 2.1 Implement manifest serialization to `manifest.webmanifest` (start_url/scope resolved from base URL; `application/manifest+json` media type); emit into SSG output and serve at a stable path from the server
- [x] 2.2 Inject `<link rel="manifest">` into the document head when PWA is enabled (document builder)

## 3. Service Worker generation

- [x] 3.1 Author the framework-owned worker template (vanilla JS): resilient install-time precaching (per-entry fetch, `no-cors` for cross-origin, opaque accepted, failures logged without failing install), same-origin-only fetch dispatch for the three strategies with eviction into rule-isolated caches (max-entries/max-age), activate cleanup of old version caches, `skipWaiting`/`clientsClaim`, offline navigation fallback (embedded default page as a 200 response with `X-WebComPy-Offline` header; directory-index cache retry)
- [x] 3.2 Implement the build-time generator: embed serialized config (precache manifest, rules, fallback path, versioned cache names with config hash) into the template and emit `sw.js` into SSG output; serve the generated worker from the server with `Cache-Control: no-cache` in non-static mode
- [x] 3.3 Implement `precache="auto"` build-output enumeration (SSG pages + emitted assets, including clean URLs alongside each page's `index.html`; runtime files excluded regardless of serving mode), `precache="none"` (empty manifest), and the `precache_runtime` opt-in with per-mode size warning (local: summed bytes of runtime files; CDN: entry files only with an offline-startup caveat)

## 4. Registration and dev-mode safety

- [x] 4.1 Inject the registration script in the document builder (base-URL scope, load-time registration) when enabled; verify scope correctness under prefixed/embedded deployments
- [x] 4.2 Ensure dev mode generates/registers nothing by default and explicit enablement works (unit-level verification via the ASGI app)

## 5. Offline fallback

- [x] 5.1 Embed the default minimal offline page in the worker template; support override by user path (override file added to the precache manifest); worker navigation-fallback wiring covered by generator tests

## 6. Tests

- [x] 6.1 Unit tests: config validation (including invalid `none` + `precache_runtime` combination), manifest serialization (defaults from base URL), precache enumeration (clean URLs included, hashed assets included, runtime excluded unless opted in with per-mode warning, `none` empty), generator output contains embedded config (versioned caches, rules, fallback, offline page)
- [x] 6.2 E2E tests (Playwright): PWA-enabled app (CDN runtime, like the default static fixture) — manifest link present and fetchable, worker registers at base-URL scope (root and prefixed), offline navigation serves the prerendered page from cache via clean URL and unknown routes fall back to the offline page, new-build activation cleans old caches (dist swap). Fully-offline interpreter boot (local runtime + precache_runtime) follows the runtime_local/standalone local-only convention and is covered by unit tests instead
- [x] 6.3 Dev-mode unit test: default dev server emits no worker/registration; explicit enablement serves both paths

## 7. Docs

- [x] 7.1 docs_app PWA guide: configuration reference (`precache` auto/none, runtime opt-in per serving mode), precache trade-offs, strategy selection guidance, same-origin limitation, offline fallback customization, max-age/eviction best-effort note, dev-mode note

## 8. Validation

- [x] 8.1 `uv run ruff check .` and `uv run ruff format --check .` pass
- [x] 8.2 `uv run pyright` passes
- [x] 8.3 `uv run python -m pytest tests/ --tb=short` passes
