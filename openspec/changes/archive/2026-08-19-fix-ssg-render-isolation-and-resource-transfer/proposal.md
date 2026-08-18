# Proposal: fix-ssg-render-isolation-and-resource-transfer

## Why

SSG-generated pages are not isolated from each other: shared mutable state leaks across the per-page render contexts, so each page's output depends on the route generation order. Two user-visible defects result:

1. **Missing scoped styles**: `docs_app`'s Documents pages ship without the `DocsSidebar` scoped style (verified on the deployed site: sidebar markup is present but its `<style data-webcompy-cid>` element is absent, so section toggles render as UA-default buttons and links render unstyled until WebComPy boots and re-injects styles client-side).
2. **Order-dependent hydration payloads**: the shared `ServerResourcePort` accumulates loaded resources across all page generations, so a page's transfer payload contains every resource loaded by previously generated pages (verified: the Installation page embeds 1 markdown file, the Typed Realtime page embeds 9). Users landing on "early" pages get no resource cache and see a fetch + content flash on every document navigation; users landing on "late" pages get a silently bloated payload.

Both violate the same invariant the `render-context` spec already states: no mutable state shall be shared between render contexts, and SSG output shall be reproducible regardless of generation order. Additionally, users of the docs site want flicker-free document navigation to be a guaranteed behavior, which requires a deterministic way to ship all text resources in every page's payload.

## What Changes

- **Component registration registry**: every `ComponentGenerator` ever created is tracked process-wide and re-registered into each new render context's `ComponentStore`, so scoped-style coverage no longer depends on whether a component module was first imported with or without an active DI scope (fixes missing styles for layout-imported components such as `DocsSidebar`, and for lazy routes on the dev/prod server).
- **Post-render head collection**: scoped-style (and reactive scoped-style) HTML collection moves after the component tree render and after pending async tasks settle, so components registered during the render and reactive styles created during async setup are included in the emitted `<head>`.
- **Per-context transfer state**: resource recordings and fetch response caches used for hydration payloads are isolated per render context, so a page's payload contains only what that page actually loaded (in default mode). Same fix applies to both `ServerResourcePort._recorded` and `ServerFetchPort._response_cache`.
- **Full text-resource transfer mode (opt-in)**: new build-config option to embed every allow-listed text resource (e.g., markdown) in every generated page's hydration payload, guaranteeing that client-side navigation never fetches those resources. `docs_app` enables it.
- **Browser resource prefetch API**: `ResourcePort` gains a `preload(paths)` capability that primes the browser fetch cache during idle time after boot, as a mitigation for apps that do not enable full transfer. `docs_app` uses it for the docs manifest sources as a defense-in-depth measure.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `scoped-css-incremental`: every component generator must be registered in every render context's component store, and SSG scoped-style collection must run after the render completes, so SSG/style coverage no longer depends on import timing or generation order.
- `reactive-scoped-style`: reactive scoped styles created during (possibly async) component setup must appear in SSG/prerendered head output, not only in the browser.
- `render-context`: the per-request isolation requirement is extended to component-generator registration visibility and to transfer-recording state (recorded resources, cached fetch responses).
- `hydration-data-transfer`: resource and fetch transfer entries must reflect only the current render context's activity in default mode; adds an opt-in mode transferring all allow-listed text resources on every page.
- `resource-port`: the port gains a `preload()` operation that primes the browser-side resource/fetch cache without blocking rendering (server-side no-op).
- `app-config`: `WebComPyBuildConfig` gains a resource-transfer mode setting (default per-page `"used"` resources, opt-in `"all-text"`).
- `ssg-via-ssr`: generated page output (head styles and hydration payload) must be deterministic and independent of route generation order.

## Known Issues Addressed

- SSG pages miss scoped styles for components whose modules are first imported while a DI scope is active (e.g., layout-only imports like `DocsSidebar`); on the dev/prod server, lazily imported page components miss the head styles on every request.
- Reactive scoped styles (`data-webcompy-cid-rx`) never appear in SSG output because they are created during setup, after styles are collected.
- Hydration payloads accumulate resources (and fetch cache entries) across SSG page generations, making output order-dependent and bloating later pages.
- Document navigation on the docs site flashes/fetches markdown when the entry page's payload did not happen to include the target document.

## Non-goals

- Teleport SSR emits anchor-only output for the navbar dropdown menus; changing that behavior is out of scope.
- Full transfer of binary resources (images, etc.) — the opt-in mode is limited to text resources to bound payload growth.
- Fetch-transfer "transfer everything" mode — only resources get the full-transfer mode; fetch transfer is only fixed to be per-context.
- Reworking the lazy-route mechanism itself — `lazy()` stays as-is and remains exercised by `docs_app`.
- Markdown fetch elimination for apps that stay on the default `"used"` transfer mode (they get the `preload()` mitigation instead).

## Impact

- **Code**: `webcompy/components/_generator.py` (registry), `webcompy/app/_render_context.py` (re-registration), `webcompy_server/_html.py` (collection ordering), `webcompy_server/_context.py` (per-context ports), `webcompy_server/ports/_resource.py` / `_fetch.py` (recording isolation), `webcompy/hydration/_collect.py` (payload sources, all-text mode), `webcompy/ports/_resource.py` + `webcompy/ports/_browser/_resource.py` (`preload()`), `webcompy_cli/config/_build_config.py` (new setting), `webcompy_cli/_generate.py` (mode wiring).
- **Apps**: `docs_app/webcompy_config.py` enables full text-resource transfer; `docs_app` root component primes the docs manifest via `preload()`.
- **APIs**: additive only — new `ResourcePort.preload()`, new build-config field. No breaking changes.
- **Specs**: 7 modified capabilities (see above).
- **Tests**: new unit tests for registration coverage, payload isolation, transfer modes, and collection ordering; E2E assertion that docs navigation performs no resource fetch when full transfer is enabled.
