# Tasks: feat-pwa

## 1. Configuration

- [ ] 1.1 Add `ManifestConfig` and `PWAConfig` dataclasses to the webcompy-cli build config (`enabled`, manifest fields, `precache` mode, `precache_runtime`, runtime rules list (pattern/strategy/max-entries/max-age), offline fallback path); defaults keep PWA off; wire into `WebComPyBuildConfig`
- [ ] 1.2 Validate config combinations at build start (unknown strategy names, invalid patterns, fallback path existence) with actionable errors

## 2. Manifest pipeline

- [ ] 2.1 Implement manifest serialization to `manifest.webmanifest` (start_url/scope resolved from base URL); emit into SSG output and serve at a stable path from the server
- [ ] 2.2 Inject `<link rel="manifest">` into the document head when PWA is enabled (document builder)

## 3. Service Worker generation

- [ ] 3.1 Author the framework-owned worker template (vanilla JS): install-time precaching, fetch dispatch for the three strategies with eviction (max-entries/max-age), activate cleanup of old version caches, `skipWaiting`/`clientsClaim`, offline navigation fallback
- [ ] 3.2 Implement the build-time generator: embed serialized config (precache manifest, rules, fallback path, versioned cache names) into the template and emit `sw.js` into SSG output; serve the generated worker from the server in non-static mode
- [ ] 3.3 Implement `precache="auto"` build-output enumeration (SSG pages + emitted assets) and the `precache_runtime` opt-in with the build-time size warning

## 4. Registration and dev-mode safety

- [ ] 4.1 Inject the registration script in the document builder (base-URL scope, load-time registration) when enabled; verify scope correctness under prefixed/embedded deployments
- [ ] 4.2 Ensure dev mode generates/registers nothing by default; explicit dev enablement path documented and tested

## 5. Offline fallback

- [ ] 5.1 Ship the default minimal offline page asset; support override by user path; worker navigation-fallback wiring covered by template tests

## 6. Tests

- [ ] 6.1 Unit tests: config validation, manifest serialization (defaults from base URL), precache enumeration (hashed assets included, runtime excluded unless opted in + warning logged), generator output contains embedded config
- [ ] 6.2 E2E tests (Playwright): PWA-enabled app — manifest link present and fetchable, worker registers at base-URL scope, precached assets served from cache (offline emulation), offline navigation serves the fallback, new-build activation cleans old caches (simulated)
- [ ] 6.3 Dev-mode test: default dev server emits no worker/registration

## 7. Docs

- [ ] 7.1 docs_app PWA guide: configuration reference, precache trade-offs (runtime opt-in size), strategy selection guidance, offline fallback customization, dev-mode note; demo configuration in docs_app if feasible within size limits

## 8. Validation

- [ ] 8.1 `uv run ruff check .` and `uv run ruff format --check .` pass
- [ ] 8.2 `uv run pyright` passes
- [ ] 8.3 `uv run python -m pytest tests/ --tb=short` passes
