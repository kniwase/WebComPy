---
title: Progressive Web App
description: Enable installability and offline support declaratively with PWAConfig — build-time Web App Manifest and framework-owned Service Worker generation, precaching, runtime caching decision rules, and offline navigation fallback.
---

# Progressive Web App

WebComPy turns static and server-rendered applications into installable, offline-capable Progressive Web Apps from declarative Python configuration (`PWAConfig`), following the Angular `ngsw` model with **zero user JavaScript** and **zero third-party Service Worker libraries**.

At build time (`webcompy generate`) or serving startup (`create_asgi_app()`), WebComPy serializes `manifest.webmanifest`, generates an auditable vanilla-JS Service Worker (`sw.js`) with your effective configuration embedded inline, injects the `<link rel="manifest">` head tag, and registers the worker scoped to `base_url`. PWA support is **disabled by default** until you explicitly enable it.

## When to use

- **Installable SSG sites and offline-ready apps** — enable `PWAConfig(enabled=True, ...)` to precache generated routes, cache runtime API/static fetches declaratively, and serve a clean offline fallback page.
- **Purely dynamic server-authenticated apps or active local hot-reload** — leave `PWAConfig` at its default (`enabled=False`) so neither manifest links nor a caching worker intercept live requests.
- **Pair with pre-rendered assets and SSR transfers** — combine PWA precaching with [SSR & SSG](/documents/advanced/ssr-and-ssg) and [Hydration & Data Transfer](/documents/advanced/hydration-and-transfer).

## Setup

Configure `pwa` on `WebComPyBuildConfig` inside `webcompy_config.py`:

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
        ),
        precache="auto",
        precache_runtime=False,
        runtime=[
            RuntimeCachingRule(pattern="/api/", strategy="network-first", max_entries=50, max_age=300),
            RuntimeCachingRule(pattern="static/**", strategy="stale-while-revalidate"),
        ],
        fallback_path=None,
    ),
)
```

`PWAConfig.validate()` runs at build start before artifacts resolve and raises `WebComPyException` with an actionable error if `enabled=True` lacks `manifest`, `precache` / `display` / `strategy` uses an unsupported value, `precache="none"` is combined with `precache_runtime=True`, a runtime pattern includes `"://"` (cross-origin), `max_entries`/`max_age` is non-positive or boolean, or `fallback_path` escapes or does not exist inside `static_files_dir`.

## What gets generated

When `pwa.enabled` is `True`, the build and serving pipeline produces artifacts on disk / HTTP routes and injects matching tags into rendered HTML:

```text
WebComPyBuildConfig(pwa=PWAConfig(...))
  ├──► manifest.webmanifest        (<link rel="manifest"> injected in <head>)
  ├──► sw.js                       (framework template + embedded JSON config + sha256 version)
  └──► <body> registration script  (navigator.serviceWorker.register("{base_url}sw.js", {scope}))
```

### Web App Manifest

`ManifestConfig` serializes to `manifest.webmanifest` (`application/manifest+json`) in the `dist/` output during `webcompy generate` and is served by `create_asgi_app()` at `{base_url}manifest.webmanifest`. Document HTML automatically receives `<link rel="manifest" href="{base_url}manifest.webmanifest">` inside `<head>`.

`start_url` and `scope` default to `app.config.base_url`, so prefixed or embedded mounts work without duplicating base paths. Icon paths (`ManifestIcon.src`) are placed inside your app's `static_files_dir` and resolved relative to `base_url`. Supported `display` values are `"fullscreen"`, `"standalone"` (default), `"minimal-ui"`, and `"browser"`.

### Framework-owned Service Worker

Instead of accepting user-written Service Worker JavaScript, WebComPy ships a small, self-contained vanilla-JS worker template and embeds your serialized configuration (`precache`, `runtime`, `fallback`, `offlineHtml`, `version`) directly into the emitted `sw.js`:

- **Offline from first install**: Because all precache entries, caching rules, and the default offline HTML live inline inside `sw.js`, the worker never needs a startup network fetch to configure itself.
- **Deterministic config rotation**: WebComPy hashes the serialized PWA config with SHA-256 (12 hex characters) and appends it to `app_version` (`"{app_version}-{digest}"`), guaranteeing a byte-different `sw.js` and new cache generation whenever rules, precached outputs, or fallback paths change.
- **Fresh delivery headers**: When served dynamically, `sw.js` uses `application/javascript` and `Cache-Control: no-cache` so browsers always revalidate the worker script on navigation.

Keeping worker behavior declarative avoids arbitrary JavaScript drift across dual-environment Python builds and ensures zero third-party JS dependencies.

### Precache

- **`precache="auto"` (default)**: During `webcompy generate`, enumerates every emitted file in `dist/` (excluding `manifest.webmanifest`, `sw.js`, and Python runtime files unless `precache_runtime=True`) using scope-relative paths. Each generated `.../index.html` adds **both** its file path (`about/index.html`) and its clean URL (`./` or `about/`) so offline navigations hit the precache directly. Dynamic server starts (`create_asgi_app` without SSG `dist_dir`) include only explicit opt-in entries (`fallback_path` / `precache_runtime`) in precache. Content-hashed lockfile assets rotate their URLs on each build.
- **`precache="none"`**: Skips output-directory enumeration completely. If `fallback_path` is set, that custom offline page remains the manifest's sole precache entry so offline fallbacks still succeed.
- **`precache_runtime=True` (opt-in)**: Python runtime files (PyScript + Pyodide bundles) are excluded by default because they require tens of megabytes of device storage. Setting `precache_runtime=True` logs a build-time warning to `stderr`:
  - With **local runtime serving** (`standalone=True` or `runtime_serving="local"`), logs the summed megabyte total and adds local runtime files for a self-contained offline cold start.
  - With **CDN runtime serving**, adds only known entry URLs (PyScript core CSS/JS and the Pyodide lockfile) and warns that offline startup is not guaranteed because cross-origin requests pass through unintercepted at fetch time.

### Service Worker registration

Every rendered document receives an inline body script waiting for the `window` `"load"` event and registering the worker scoped to `base_url`:

```javascript
if ("serviceWorker" in navigator) {
  window.addEventListener("load", function () {
    navigator.serviceWorker.register("/sw.js", { scope: "/" });
  });
}
```

Prefixed apps (such as `base_url="/portal/"`) automatically emit `"/portal/sw.js"` with `{ scope: "/portal/" }`.

## What runs in the browser

Once registered, `sw.js` handles `install`, `activate`, and same-origin `GET` `fetch` events using isolated caches prefixed with `webcompy-pwa-`.

### Runtime caching

Choose a `RuntimeCachingStrategy` in `RuntimeCachingRule` by matching resource kind to freshness vs latency requirements:

| Resource kind | Strategy | When to pick it | Configuration snippet |
|---|---|---|---|
| Content-hashed or immutable static assets (`/assets/app.3f8a.js`, vendor bundles) | `cache-first` | Content hashes guarantee a URL never changes; return cached copy immediately and hit network only on miss or expired `max_age` | `RuntimeCachingRule(pattern="/assets/**", strategy="cache-first", max_entries=100)` |
| Dynamic JSON APIs & SSR endpoints (`/api/`, `/_webcompy-resource/`) | `network-first` | Always prefer fresh server data when online; serve the last cached response only when network fails | `RuntimeCachingRule(pattern="/api/", strategy="network-first", max_entries=50, max_age=300)` |
| Semi-static media, icons, or downloadable docs (`static/**`, `/media/*`) | `stale-while-revalidate` | Respond instantaneously from cache while updating the entry in the background for subsequent loads | `RuntimeCachingRule(pattern="static/**", strategy="stale-while-revalidate", max_entries=60, max_age=86400)` |
| Unmatched same-origin routes & all cross-origin / non-GET requests | Pass-through (no rule) | Requests that must never be implicitly cached (auth mutations, external CDNs, tracking) | Omit from `runtime=[...]` |

Pass a list of ordered rules to `PWAConfig.runtime` (first matching rule wins):

```python
from webcompy_cli.config import ManifestConfig, PWAConfig, RuntimeCachingRule

pwa = PWAConfig(
    enabled=True,
    manifest=ManifestConfig(name="Portal App", short_name="Portal"),
    runtime=[
        RuntimeCachingRule(pattern="/assets/**", strategy="cache-first", max_entries=100),
        RuntimeCachingRule(pattern="/api/", strategy="network-first", max_entries=50, max_age=300),
        RuntimeCachingRule(pattern="static/**", strategy="stale-while-revalidate", max_entries=60, max_age=86400),
    ],
)
```

Matching and eviction mechanics:

- **Pattern syntax**: Patterns without `"*"` match by scope-relative pathname prefix (`"/api/"`). Patterns containing `"*"` compile to regular expressions where `"*"` matches one path segment (`[^/]*`) and `"**"` matches across slashes (`.*`). A missing leading `"/"` (like `"static/**"`) is normalized automatically to `"/static/**"`.
- **Full-URL rule cache keys**: Runtime rules cache against full `Request` URLs, so `?page=1` and `?page=2` stay separate. Same-origin `GET` requests only; non-`GET` and cross-origin requests bypass `sw.js`.
- **Isolated rule caches & bounds**: Precache lives in `webcompy-pwa-v-{version}`; each rule at index `i` writes to its own `webcompy-pwa-r{i}-{version}` cache. Setting `max_entries` trims oldest keys per rule cache without touching precache or sibling rules; `max_age` expires freshness checks in seconds best-effort within the active worker's lifetime.

### Activation, updates, and cache cleanup

- **Resilient install + immediate skip**: During `install`, missing or failing individual precache URLs log `[webcompy-pwa] precache failed:` warnings via `console.warn` instead of aborting installation, then `install` calls `self.skipWaiting()`.
- **Old-cache rotation + immediate control**: During `activate`, the worker deletes every `webcompy-pwa-*` cache whose name does not belong to the active version (`PRECACHE_NAME` and current `ruleCacheName(i)`) and calls `self.clients.claim()`, taking control immediately on new builds.

### Offline fallback

Only navigation requests (`request.mode === "navigate"`) trigger offline fallback handling:

1. Check cached navigations query-insensitively (`ignoreSearch: true`); for extensionless clean paths, retry `{pathname}/index.html`.
2. On cache miss, fetch from the network.
3. If the network throws while offline, return either your precached `fallback_path` response or the embedded framework HTML page with HTTP `200` and response header `X-WebComPy-Offline: fallback`.

Configure a custom offline page relative to `static_files_dir`:

```python
from webcompy_cli.config import ManifestConfig, PWAConfig

pwa = PWAConfig(
    enabled=True,
    manifest=ManifestConfig(name="Docs Portal"),
    fallback_path="offline.html",
)
```

Non-navigation failures (such as an uncached XHR call) follow their matching runtime rule or propagate the network error normally.

## Recipes

### 1. Fully offline cold start with local runtime precaching

Combine `standalone=True` (local runtime and package wheels) with `precache_runtime=True` so first-time cold boots succeed with no internet connection:

```python
import my_app.app as app_module

from webcompy_cli.config import ManifestConfig, PWAConfig, WebComPyBuildConfig

config = WebComPyBuildConfig(
    app_module,
    standalone=True,
    pwa=PWAConfig(
        enabled=True,
        manifest=ManifestConfig(name="Field Inspector", short_name="Inspector"),
        precache="auto",
        precache_runtime=True,
    ),
)
```

### 2. Prefixed deployment with a custom offline page

Set `base_url` on `WebComPyAppConfig` and ship `static/offline.html` alongside your app:

```python
from webcompy.app import WebComPyApp, WebComPyAppConfig
from webcompy.components import ComponentContext, define_component
from webcompy.elements import html
from webcompy_cli.config import ManifestConfig, PWAConfig, WebComPyBuildConfig
import my_app.app as app_module


@define_component()
def Root(context: ComponentContext[None]):
    return html.MAIN({}, "Prefixed PWA root")


app = WebComPyApp(
    root_component=Root,
    config=WebComPyAppConfig(base_url="/portal/"),
)

build_config = WebComPyBuildConfig(
    app_module,
    pwa=PWAConfig(
        enabled=True,
        manifest=ManifestConfig(name="Customer Portal", short_name="Portal"),
        fallback_path="offline.html",
    ),
)
```

`manifest.webmanifest` defaults `start_url` and `scope` to `"/portal/"`, `<link rel="manifest">` points to `"/portal/manifest.webmanifest"`, and registration registers `"/portal/sw.js"` with `{ scope: "/portal/" }`.

### 3. Observing install, activation, and update rotation locally

Exercise the generated worker against static output (`localhost` is a secure context for Service Workers):

1. Generate the static build and serve the output directory:

```bash
uv run python -m webcompy generate --config my_app.webcompy_config
python3 -m http.server -d dist 8080
```

2. Open `http://localhost:8080/` in your browser, open **DevTools → Application → Service Workers & Cache Storage** (or evaluate in the console):

```javascript
const reg = await navigator.serviceWorker.getRegistration();
console.log("scope:", reg?.scope, "active:", Boolean(reg?.active));
console.log("caches:", await caches.keys());
```

3. Verify `webcompy-pwa-v-<version>-<hash>` and any rule caches appear, toggle **Offline** in DevTools Network, and visit both a generated route (serves precached `index.html`) and an un-generated URL like `/never-built/` (serves your fallback page).
4. Change a rule in `PWAConfig.runtime` (or bump the app version), re-run `webcompy generate`, and reload or call `await reg.update()` — inspect `caches.keys()` to verify new `webcompy-pwa-*-<new-hash>` caches appear while previous-version caches are deleted immediately upon activation.

## Behavior notes

- **Development mode off by default**: `PWAConfig.enabled` defaults to `False` so `webcompy start --dev` emits no manifest, no worker, and no registration script, preventing cached worker responses from hiding hot-reloaded Python edits. Explicitly setting `enabled=True` activates PWA in dev mode as well; gate `enabled` on an environment flag if you share one `webcompy_config.py`, and test worker behavior primarily against `webcompy generate` or production mode.
- **Reserved output filenames**: `manifest.webmanifest` and `sw.js` are reserved outputs. Static files with those names under `static_files_dir` are shadowed and emit a `stderr` warning during serving.
- **Current scope boundaries**: Custom Service Worker scripts/fragments, push notifications, background sync, iOS-specific meta tags outside the manifest, and user-prompted update banners ("click to refresh") are out of scope in the current release.

## Pitfalls

- **Unconditional `enabled=True` during `webcompy start --dev`**: Active Service Worker caches will fight dev-server hot reload (`_webcompy_reload`) unless you unregister the worker in DevTools or guard `enabled` by environment.
- **Expecting offline cold start with `precache_runtime=True` on CDN**: With default CDN runtime serving, `sw.js` does not intercept cross-origin requests; set `standalone=True` (or `runtime_serving="local"`) when you need genuine offline boot.
- **Combining `precache="none"` with `precache_runtime=True`**: Rejected immediately by `PWAConfig.validate()` because `precache="none"` builds no output precache manifest.
- **Putting scheme/origin in `RuntimeCachingRule.pattern`**: Patterns containing `"://"` fail validation — runtime rules target same-origin scope-relative paths only.
- **Mid-session activation**: Because `install` calls `skipWaiting()` and `activate` calls `clients.claim()`, deploying a new worker swaps active control immediately without prompting existing open tabs.

## Next steps

- Pair Service Worker precaching with self-hosted `standalone=True` assets in [Serving Modes](/documents/server/serving-modes).
- Understand the build pipeline and `create_asgi_app()` modes in [SSR & SSG](/documents/advanced/ssr-and-ssg).
- Layer offline asset caching onto transferred text resources in [Hydration & Data Transfer](/documents/advanced/hydration-and-transfer).
- Configure the boot experience shown while PyScript loads in [Loading Screen](/documents/advanced/loading-screen).
- Compare client storage and cookie lifecycles in [Persistence Patterns](/documents/advanced/persistence-patterns).
