# Design: feat-pwa

## Context

PWA support decomposes into the Web App Manifest (JSON metadata — straightforward) and the Service Worker (pure JavaScript — the part that conflicts with WebComPy's "no JavaScript" promise unless the framework generates it). Industry shapes: Angular's `@angular/service-worker` (ngsw) generates a framework-owned worker from declarative config at build time; Next/Nuxt/SvelteKit wrap Workbox via plugins. Either way, the user writes configuration, never worker code. WebComPy follows the ngsw model with zero JS dependencies.

Grounded facts (verified in codebase):

- Build configuration lives in `WebComPyBuildConfig` (`webcompy_cli/config/_build_config.py`: `dist`, `static_files_dir`, `server: WebComPyServerConfig`, wheel/runtime serving modes) — `PWAConfig` attaches here.
- The SSR/SSG document builder (`webcompy_server/_html.py`) constructs the full `<html>/<head>/<body>` tree, injects head content by string replacement, and injects the app-loader script before `</body>` — both injection points the PWA needs (manifest link in head, registration script in body).
- Static files are served from a configured directory (`get_static_files`); SSG writes build output to `dist` — enumerable for precache manifests.
- Lockfile-driven dependency serving produces hashed asset names, which makes cache-first strategies safe (no silent staleness).

## Goals / Non-Goals

**Goals:**

- Declarative `PWAConfig` producing a complete PWA: manifest + generated `sw.js` + registration + offline fallback.
- Precache automation over build output with hashed assets; runtime precache opt-in.
- Three runtime caching strategies with pattern rules.
- Immediate-activation update behavior with old-cache cleanup.
- Dev-mode safety (disabled by default).

**Non-Goals:**

- Workbox, push notifications, background sync, custom SW escape hatches, update-prompt UX (see proposal Non-goals).

## Decisions

### D1: Framework-owned vanilla JS worker template (ngsw model)

The framework ships a Service Worker template (plain JS, maintained with the framework) implementing: install-time precaching, fetch-time strategy dispatch, activate-time cleanup, and offline fallback for navigations. At build time the effective PWA configuration is embedded as a JSON constant and `sw.js` is emitted. Rationale: zero new dependencies; the worker is small (precache + three strategies + fallback, on the order of a few hundred lines) and fully auditable; the framework already distributes browser-facing JS (the app loader), so the distribution path exists. Alternative (Workbox) rejected: it adds a JS dependency tree to a Python-centric build pipeline and its value over a small purpose-built worker does not justify the coupling for v1.

### D2: Configuration embedded at build time

`sw.js` is generated per build with the config serialized inline (precache list, runtime rules, fallback path, cache-name version). No runtime config fetching: the worker must work offline from its very first install. Cache storage names include the build version (plus a content hash of the embedded config, so config changes rotate caches even when the app version is static) so each deployment gets isolated caches, and the activate step deletes caches from previous versions.

### D3: Precache automation with hashed assets; runtime opt-in

`precache="auto"` enumerates the build output (SSG HTML pages and emitted assets) into the precache manifest; `precache="none"` disables enumeration entirely (no build-output entries — only a configured offline fallback override remains precached so the custom offline page keeps working offline). Because lockfile-driven assets carry content hashes in their names, cache-first serving cannot silently serve stale content — a new deployment means new URLs. Precaching the Python runtime (Pyodide core, PyScript bundles) enables fully offline startup but costs tens of MB of device storage; it is opt-in (`precache_runtime`), runtime files are excluded from automatic enumeration regardless of serving mode, and the build logs a size warning when enabled. Wasm dependency wheels under `_webcompy-assets/packages/` count as app assets, not runtime. See D11 for the per-serving-mode semantics of the opt-in.

### D4: Runtime caching rules

Each rule: URL pattern (prefix or glob), strategy (`cache-first`, `network-first`, `stale-while-revalidate`), optional max-entries and max-age eviction. Requests matching no rule pass through to the network untouched (no implicit caching). Rationale: explicit rules keep caching predictable; the three strategies cover the standard cases (immutable hashed assets → cache-first; API/data → network-first; semi-static content → SWR). Rules apply to same-origin requests only (D14), and their stored entries live in caches isolated from the precache (D12). Rule caches match by full URL (query string included), so different query variants are cached independently; search-insensitive matching applies to navigations only (D10).

### D5: Immediate activation (skipWaiting + clientsClaim)

The generated worker calls `skipWaiting()` on install and `clientsClaim()` on activate: new versions take effect immediately and old caches are purged on activate. Rationale: simplest correct default for content apps; the alternative (user-prompted update via a composable listening for worker updates) is deferred — it needs client-side update detection plumbing and is a v1.x enhancement, not a blocker. Navigation requests are served cache-first against the precache so instant activation is the only refresh path; precache install is resilient (D15).

### D6: Manifest generation and injection

`ManifestConfig` (name, short_name, icons list, display, theme_color, background_color, start_url defaulting to base_url, scope defaulting to base_url) serializes to `manifest.webmanifest`: written into SSG output and served by the server at a stable path. The document builder injects `<link rel="manifest">` into the head when PWA is enabled. Icon files are user-provided static assets referenced by path.

### D7: Registration injection at document build time

The document builder injects a small inline registration script (app-loader injection precedent) that registers `sw.js` at the app's base URL scope after load. Registration is skipped when PWA is disabled. Rationale: no user code, correct scope under base_url deployments (including asgi-embed prefixes, which the builder already knows).

### D8: Dev mode disabled by default

The dev server does not generate or register the Service Worker unless explicitly enabled in config: SW caching fights hot-reload and confuses development. Documented prominently.

### D9: Offline fallback for navigations

Navigation requests that fail (offline, no precached match) respond with a configured fallback page (default: a framework-provided minimal offline page; overridable by path). Non-navigation failures follow their runtime rule or pass through. The default page is a minimal HTML string embedded in the generated worker, returned with status 200 and an `X-WebComPy-Offline: fallback` header (non-2xx navigation responses risk browser error-UI interference); an overridden fallback file is added to the precache manifest and preferred when present.

### D10: Directory-index resolution for generated pages

Static hosts resolve `/documents/foo/` to `documents/foo/index.html`, but the Cache API matches exact URLs — precaching only file paths would miss every clean-URL navigation. The build-time enumeration therefore also emits each generated page's clean URL (`/` → `./`, `documents/foo/` for `documents/foo/index.html`) as a separate precache entry, and the worker's navigation handler additionally retries a cache lookup at `<pathname>/index.html` (skipping paths whose last segment contains a dot). Both mechanisms are cheap and cover prod-mode runtime caches that were stored under file URLs.

### D11: Runtime precache is per-serving-mode

Automatic enumeration excludes runtime files (the local runtime asset set: PyScript `core.js`/`core.css` and the Pyodide bundle under `_webcompy-assets/`) regardless of serving mode, so the opt-in is meaningful even for local serving. `precache_runtime` with local serving includes those dist files in the precache (fully offline startup works) and the warning states the summed byte size. With CDN serving it includes only the known entry URLs (PyScript core files and the Pyodide lock file), warns that offline startup is not guaranteed (transitive interpreter files are not enumerated), and the worker fetches those cross-origin entries with `no-cors`, caching opaque responses. `precache="none"` with `precache_runtime` is rejected at validation. Because the worker passes cross-origin requests through (D14), the opaque CDN entries are stored but never served in v1; the opt-in is effective only for local runtime serving.

### D12: Cache naming and isolation

The precache uses `webcompy-pwa-v-<version>-<hash>` and each runtime rule uses `webcompy-pwa-r<rule-index>-<version>-<hash>`, where `<version>` is the app build version and `<hash>` is a short digest of the embedded config, so config changes rotate caches even when the version string is static. The activate step keeps the current precache plus the current rule caches and deletes everything else under the `webcompy-pwa-` prefix. Max-entries trimming therefore cannot evict precached pages. Max-age tracking is in-memory (worker lifetime, best-effort); eviction order follows `cache.keys()` order, which is insertion-order in practice but unspecified — documented as best-effort.

### D13: Precache entries are scope-relative

SSG precache entries are emitted relative to the worker's scope (the base URL), e.g. `./`, `index.html`, `documents/foo/`, `_webcompy-app-package/app-0+sha.whl`; the worker resolves them against `self.location` so prefix-deployed and embedded sites cache and match the correct absolute URLs. Cross-origin CDN runtime entries are emitted as absolute URLs. Runtime rule patterns are matched against the request pathname made scope-relative (the segment after the worker's scope), so a rule like `/api/` works identically at the root and under a base-URL prefix. Patterns written without the leading slash (e.g. `static/**`) are normalized to one at generation time, because scope-relative pathnames always keep the leading slash.

### D14: Same-origin control only

The generated worker passes through any cross-origin request before rule dispatch. Deterministic, testable caching of third-party origins (opaque-response handling, CORS variance) is deferred; runtime rules are documented as same-origin-only.

### D15: Resilient precache install

Install fetches each precache entry individually (cross-origin entries with `no-cors`, opaque responses accepted) under `Promise.allSettled`, logging failures. A single 404 or network hiccup during install must not strand the app with no installed worker.

## Injection and serving topology

`webcompy-server` cannot import `webcompy-cli` (dependency direction is cli → server → core), so the document builder receives only a boolean `pwa_enabled` parameter; the manifest link href and registration script derive the stable paths `manifest.webmanifest` and `sw.js` from the base URL it already knows. Generation (manifest serialization, precache enumeration, worker emission) lives in `webcompy_cli/_pwa.py`: SSG writes both files into `dist` after all other output is complete, and the prod server generates them in memory at startup and serves them via routes registered before user static-file routes so framework values win name collisions with a build-time warning. Dev mode follows the same single `enabled` flag, whose default keeps dev safe. The server also registers each static file under the base-URL prefix (alongside the root route) so relative asset references from prefixed pages resolve to the file instead of the catch-all HTML route.

## Risks / Trade-offs

- **Worker template correctness**: vanilla JS maintained in-repo must be right across browsers; covered by E2E (install/assert precache, offline navigation to fallback) and kept deliberately small.
- **Immediate activation surprises**: in-flight sessions can see a mid-session swap on deploy. Accepted as the v1 default (documented); update-prompt UX is the deferred remedy.
- **Precache size**: auto-enumeration could precache large media; eviction limits and the runtime opt-in warning bound growth. A future budget mechanism is noted, not built.
- **asgi-embed scope alignment**: registration scope must respect base_url/prefix; the builder derives both from existing config, and embed scenarios are included in E2E.
- **E2E serving choice**: the PWA E2E app keeps the default CDN runtime to stay inside the regular (non-skipped) E2E matrix — the repo's local-runtime E2E suites are deliberately skipped in CI. Offline assertions rely on the prerendered SSG HTML (rendered DOM present in the cached document without interpreter boot); the fully-offline interpreter boot path (local runtime + `precache_runtime`) is verified by unit tests and kept as a local-only scenario.
