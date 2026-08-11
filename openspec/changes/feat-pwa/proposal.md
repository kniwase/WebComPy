# Proposal: feat-pwa

## Why

Progressive Web App support — installability and offline capability — is standard for production web apps (Nuxt/SvelteKit provide PWA modules, Angular ships `@angular/service-worker`). The core of PWA is the Service Worker, which is pure JavaScript territory: WebComPy users cannot write one without breaking the framework's "no JavaScript" promise, so the framework itself must generate it from declarative Python configuration. The Angular ngsw model proves this shape — a framework-owned worker generated at build time from config, with zero user JS — and WebComPy's lockfile-hashed assets make cache strategies unusually safe to automate.

## What Changes

- `PWAConfig` dataclass under `WebComPyBuildConfig` (server/build configuration): `enabled`, manifest settings, precache mode, runtime cache rules, offline fallback path.
- **Web App Manifest**: `ManifestConfig` (name, short_name, icons, display, theme_color, background_color, start_url defaults) serialized to `manifest.webmanifest`, emitted at build time (SSG) and served by the server, with `<link rel="manifest">` injected into the document head.
- **Service Worker generation (ngsw-style)**: the framework ships a vanilla JS worker template; at build time the effective `PWAConfig` is embedded as JSON and `sw.js` is generated into the output. No Workbox or other JS dependency.
- **Precache**: `precache="auto"` enumerates build output (SSG pages and hashed assets) into the precache manifest. Precaching the Python runtime (Pyodide/PyScript bundles) is opt-in with a size warning (tens of MB). Lockfile-hashed asset names make cache-first strategies safe by construction.
- **Runtime caching rules**: URL pattern + strategy (`cache-first`, `network-first`, `stale-while-revalidate`) with optional max-entries/max-age.
- **Update behavior**: generated worker uses `skipWaiting` + `clientsClaim` (immediate activation of new versions); old-version caches are cleaned on activate. A user-prompted update flow is deferred.
- **Offline fallback**: navigation requests that fail offline serve a configurable fallback page.
- **Registration**: the document builder injects a small registration script (app-loader precedent) registering `sw.js` at the app's base URL scope.
- **Dev mode**: PWA is disabled by default in the dev server (Service Worker caching interferes with hot reload).

## Capabilities

### New Capabilities

- `pwa`: Progressive Web App support — manifest generation/serving/injection, build-time Service Worker generation from declarative config (framework-owned worker template, no user JS), precache automation with hashed assets, runtime caching strategies, offline fallback, update behavior, registration injection, and dev-mode defaults.

### Modified Capabilities

(none)

## Impact

- **Code**: `PWAConfig`/`ManifestConfig` in webcompy-cli build config; SW template asset + generator; manifest/sw emission in the SSG pipeline and server static serving; document-builder injection (manifest link + registration script) in webcompy-server; unit and E2E tests.
- **APIs**: additive only (new config dataclasses with safe defaults; PWA off unless enabled). No breaking changes.
- **Dependencies**: none (vanilla JS worker template maintained by the framework).
- **Docs**: docs_app PWA guide (configuration, precache trade-offs, offline fallback) and a demo configuration.

## Known Issues Addressed

(none)

## Non-goals

- Workbox integration or any third-party SW library.
- User-prompted update UX (`use_pwa_update()`-style composable) — deferred to a later change; immediate activation is the v1 default.
- Push notifications, background sync, periodic background sync.
- iOS-specific meta tags beyond what the manifest covers.
- Custom Service Worker escape hatches (user-supplied sw.js fragments) — declarative config only in v1.
- Precache size budgeting/enforcement beyond the opt-in warning for runtime assets.
