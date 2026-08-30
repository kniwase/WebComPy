---
title: Progressive Web App
description: Enable installability and offline support declaratively — the framework generates the Web App Manifest and a framework-owned Service Worker at build time, so no JavaScript is required.
---

# Progressive Web App

A Progressive Web App (PWA) can be installed to a device and keeps working offline. The core of a PWA is the Service Worker — pure JavaScript that WebComPy generates for you from declarative Python configuration. You never write worker code: the framework ships a small, auditable worker, embeds your build configuration into it at build time, injects the Web App Manifest link, and registers the worker at the correct scope. This follows the Angular `ngsw` model with zero third-party JavaScript dependencies.

PWA support is **off by default**. Nothing is emitted — no manifest, no worker, no registration — until you enable it.

## Configuration

PWA is configured on `WebComPyBuildConfig.pwa`, alongside the other build options in `webcompy_config.py`:

```python
import my_app.app as app_module

from webcompy_cli.config import (
    ManifestConfig,
    ManifestIcon,
    PWAConfig,
    RuntimeCachingRule,
    WebComPyBuildConfig,
)

config = WebComPyBuildConfig(
    app_module,
    pwa=PWAConfig(
        enabled=True,
        manifest=ManifestConfig(
            name="My Application",
            short_name="MyApp",
            icons=[
                ManifestIcon(src="icons/icon-192.png", sizes="192x192", type="image/png"),
                ManifestIcon(src="icons/icon-512.png", sizes="512x512", type="image/png"),
            ],
            display="standalone",
            theme_color="#1d4ed8",
            background_color="#ffffff",
            # start_url and scope default to the app base URL
        ),
        precache="auto",
        precache_runtime=False,
        runtime=[
            RuntimeCachingRule(pattern="/_webcompy-resource/", strategy="network-first", max_entries=50),
            RuntimeCachingRule(pattern="static/**", strategy="stale-while-revalidate"),
        ],
        fallback_path=None,
    ),
)
```

Icon files are ordinary static assets you place under the static files directory (`icons/icon-192.png` above). Their paths are resolved relative to the app base URL.

## The Web App Manifest

When enabled, the framework serializes `ManifestConfig` to `manifest.webmanifest`, writes it into the static build output, serves it at `manifest.webmanifest` relative to the base URL (`application/manifest+json`), and injects `<link rel="manifest">` into every rendered page. `start_url` and `scope` default to the app base URL, so a prefixed or embedded deployment resolves them correctly without extra configuration.

## Precache

`precache="auto"` enumerates the build output — the generated pages and their emitted assets — into the worker's precache manifest at build time. Each generated page contributes both its `index.html` file path **and** its clean URL, so an offline navigation to `/about/` serves the cached document even though the file on disk is `about/index.html`.

Because lockfile-driven assets carry a content hash in their name, a new deployment means new URLs, and cache-first serving cannot return stale content for them.

Use `precache="none"` to ship an empty precache manifest (for example, when every route is dynamic and you only want runtime caching and the offline fallback):

```python
pwa=PWAConfig(enabled=True, manifest=..., precache="none")
```

### Precaching the Python runtime

By default the Python runtime (Pyodide/PyScript bundle) is excluded from the precache, even when it is served locally. Precaching it enables a fully offline cold start but costs tens of megabytes of device storage, so it is opt-in via `precache_runtime`:

```python
pwa=PWAConfig(enabled=True, manifest=..., precache_runtime=True)
```

Enabling it logs a build-time warning. With **local** runtime serving the warning states the summed size and the worker precaches the local runtime files. With a **CDN** runtime only the known runtime entry files (PyScript core and the Pyodide lock file) are precached — the warning notes that offline startup is therefore not guaranteed. For a dependable offline cold start, serve the runtime locally (for example `standalone=True`) and set `precache_runtime=True`. Combining `precache="none"` with `precache_runtime` is rejected at validation.

## Runtime caching

Each `RuntimeCachingRule` matches same-origin requests by URL `pattern` — a path prefix (`"/api/"`) or a glob with `*` (single segment) and `**` (any depth, `"static/**"`) — matched against the path relative to the app scope, and applies one of three strategies:

- `cache-first` — return the cached copy when present (and fresh), otherwise hit the network and cache the result. Best for immutable, hashed assets.
- `network-first` — try the network and fall back to cache when offline. Best for API data and other content you want fresh when possible.
- `stale-while-revalidate` — return the cached copy immediately (when fresh) and refresh the cache in the background. Best for semi-static content.

Optional `max_entries` bounds a rule's cache size (entries beyond the limit are evicted from the least-recently-stored end) and `max_age` (in seconds) treats an entry as stale after that time. Both limits are enforced best-effort: max-age is tracked for the current worker lifetime, and eviction order follows the browser's cache iteration order.

Requests matching no rule pass straight through to the network — the framework never caches anything you did not ask for. Cross-origin requests are also left untouched, so runtime rules apply only to your own origin. Rule caches match by full URL, so requests with different query strings are cached and served independently; query-insensitive matching applies to navigation requests only.

## Offline fallback

When an offline user navigates to a route that is not in the cache, the worker returns a minimal offline page provided by the framework, as a successful response with an `X-WebComPy-Offline: fallback` header. Override it with `fallback_path`, set to a file (relative to the static files directory) you ship with your app — that file is added to the precache manifest automatically:

```python
pwa=PWAConfig(enabled=True, manifest=..., fallback_path="offline.html")
```

Only navigation requests fall back. Failures for non-navigation requests follow their runtime rule or surface the network error normally.

## Updates and cache cleanup

The generated worker activates new versions immediately: it calls `skipWaiting()` on install and `clientsClaim()` on activate, so a deploy takes control of open clients without a reload. Cache names embed the build version and a hash of the effective config, so changing precached content, rules, or the fallback rotates the caches and the previous version's caches are deleted on activate. Immediate activation means an in-flight session can swap to a new build mid-session; a user-prompted update flow is planned for a later release.

## Service Worker registration

When enabled, the document builder injects a small registration script that registers `sw.js` scoped to the app base URL after load, again respecting the base-URL prefix for embedded and prefixed deployments. The worker is served from the framework's own route (`sw.js`, `application/javascript`, `Cache-Control: no-cache`). You provide no worker code and no registration code.

## Development mode

The dev server keeps PWA support disabled by default and does not register a worker, because Service Worker caching interferes with hot reload. This is driven by the same `enabled` flag, whose default (`False`) protects development. If you need to exercise the worker locally, run the built static output (`webcompy generate` then serve `dist`) rather than enabling it under the dev server.

## Notes and limitations

- The worker template is a small, framework-owned vanilla JS file with no third-party dependency, maintained alongside the framework.
- Custom Service Worker fragments, push notifications, background sync, and iOS-specific meta tags beyond the manifest are out of scope for v1.
- PWA output names (`manifest.webmanifest`, `sw.js`) are reserved; if a static file shares one of these names the framework-generated file takes precedence and the build logs a warning.
