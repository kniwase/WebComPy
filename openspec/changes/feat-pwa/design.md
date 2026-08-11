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

`sw.js` is generated per build with the config serialized inline (precache list, runtime rules, fallback path, cache-name version). No runtime config fetching: the worker must work offline from its very first install. Cache storage names include the build version so each deployment gets isolated caches, and the activate step deletes caches from previous versions.

### D3: Precache automation with hashed assets; runtime opt-in

`precache="auto"` enumerates the build output (SSG HTML pages and emitted assets) into the precache manifest. Because lockfile-driven assets carry content hashes in their names, cache-first serving cannot silently serve stale content — a new deployment means new URLs. Precaching the Python runtime (Pyodide core, PyScript bundles) enables fully offline startup but costs tens of MB of device storage; it is opt-in (`precache_runtime`) and the build logs a size warning when enabled. Default precache covers app pages/assets only.

### D4: Runtime caching rules

Each rule: URL pattern (prefix or glob), strategy (`cache-first`, `network-first`, `stale-while-revalidate`), optional max-entries and max-age eviction. Requests matching no rule pass through to the network untouched (no implicit caching). Rationale: explicit rules keep caching predictable; the three strategies cover the standard cases (immutable hashed assets → cache-first; API/data → network-first; semi-static content → SWR).

### D5: Immediate activation (skipWaiting + clientsClaim)

The generated worker calls `skipWaiting()` on install and `clientsClaim()` on activate: new versions take effect immediately and old caches are purged on activate. Rationale: simplest correct default for content apps; the alternative (user-prompted update via a composable listening for worker updates) is deferred — it needs client-side update detection plumbing and is a v1.x enhancement, not a blocker.

### D6: Manifest generation and injection

`ManifestConfig` (name, short_name, icons list, display, theme_color, background_color, start_url defaulting to base_url, scope defaulting to base_url) serializes to `manifest.webmanifest`: written into SSG output and served by the server at a stable path. The document builder injects `<link rel="manifest">` into the head when PWA is enabled. Icon files are user-provided static assets referenced by path.

### D7: Registration injection at document build time

The document builder injects a small inline registration script (app-loader injection precedent) that registers `sw.js` at the app's base URL scope after load. Registration is skipped when PWA is disabled. Rationale: no user code, correct scope under base_url deployments (including asgi-embed prefixes, which the builder already knows).

### D8: Dev mode disabled by default

The dev server does not generate or register the Service Worker unless explicitly enabled in config: SW caching fights hot-reload and confuses development. Documented prominently.

### D9: Offline fallback for navigations

Navigation requests that fail (offline, no precached match) respond with a configured fallback page (default: a framework-provided minimal offline page; overridable by path). Non-navigation failures follow their runtime rule or pass through.

## Risks / Trade-offs

- **Worker template correctness**: vanilla JS maintained in-repo must be right across browsers; covered by E2E (install/assert precache, offline navigation to fallback) and kept deliberately small.
- **Immediate activation surprises**: in-flight sessions can see a mid-session swap on deploy. Accepted as the v1 default (documented); update-prompt UX is the deferred remedy.
- **Precache size**: auto-enumeration could precache large media; eviction limits and the runtime opt-in warning bound growth. A future budget mechanism is noted, not built.
- **asgi-embed scope alignment**: registration scope must respect base_url/prefix; the builder derives both from existing config, and embed scenarios are included in E2E.
