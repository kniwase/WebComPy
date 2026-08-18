# Design: fix-ssg-render-isolation-and-resource-transfer

## Context

See proposal.md "Why" for the motivating defects. Current-state facts that shape the approach:

- `RenderContext.__init__` creates a fresh `ComponentStore` per context and calls `_register_deferred_components()`, which only iterates `_unregistered_generators` — a list a generator enters **only** when its `__init__` ran with no active DI scope. Generators created while a scope is active (lazy resolution during a request, e.g., via `RouterView._on_set_parent` → `preload_lazy_routes()`) register directly into that one context and are invisible to all later contexts.
- `_generate_html_impl` collects head/scoped-style HTML **before** rendering the component tree; `generate_html` awaits pending async work only after `_generate_html_impl` returns. Style/head insertion into the HTML string already happens last, so only the *collection* calls need to move.
- `configure_server_context` stores one `ServerResourcePort` and one `ServerFetchPort` on the app; every render context provides those shared instances, so `_recorded` and `_response_cache` accumulate across SSG pages and server requests.
- `BrowserFetchPort` already keeps a session `_response_cache` that `fetch()` checks first, and `BrowserResourcePort._fetch_bytes` goes through `fetch()` — so priming the fetch cache is sufficient to make later `load_text` calls network-free.
- SSG preload in `_generate.py` iterates the flattened `app.routes` (leaf routes only); `Router.preload_lazy_routes()` walks the full page tree including parent/layout routes.

## Goals / Non-Goals

**Goals:**
- Uniform component-registration visibility across render contexts (import-timing independent).
- Prerendered `<head>` reflects everything registered/created during the render, including async setups.
- Transfer payload contents are deterministic per page: per-context by default, explicitly full for text resources when opted in.
- A browser-side `preload()` primitive that makes resource loads network-free after idle priming.

**Non-Goals:**
- Changing the lazy-route or Teleport SSR semantics.
- Fetch-response "transfer everything" mode (fetch transfer only becomes per-context).
- Binary resource embedding in payloads.
- Multi-app registry semantics (existing cross-app guard behavior is preserved as-is).

## Decisions

### D1: Process-wide component generator registry

**Decision**: Track every created `ComponentGenerator` in a module-level registry and register all of them into each new render context's store.

- In `ComponentGenerator.__init__`, append `self` to the registry unconditionally (even when `_try_register()` succeeds immediately). Rename `_unregistered_generators` to `_all_component_generators` (private, safe to rename) and update `_register_deferred_components()` to iterate it; `_try_register()`'s existing per-store dedup (`self._name not in store.components`) and cross-app guard (`_registered_app is not app`) keep this correct and idempotent.
- `LazyComponentGenerator` does not call `super().__init__()` and never enters the registry — only resolved generators do. This is correct: proxies carry no style of their own until resolved.

**Alternatives considered**:
- *Register-on-render* (each `Component` ensures its generator is in the current store during render): corrects coverage too, but touches the hot render path and still needs D2 to surface same-render registrations in the head. Registry is smaller and centralized.
- *Fix only the SSG preload to walk the full route tree*: still leaves dev/prod serving and any non-route-triggered import broken. Done anyway as D5, but as defense-in-depth, not as the fix.

### D2: Collect head content after render and after pending async work

**Decision**: Move the `get_head_content_html()` / `get_scoped_styles_html()` calls (and their string-insertion steps) out of `_generate_html_impl` and into `generate_html`, after `await scheduler.await_pending()`.

- `_generate_html_impl` keeps assembling and rendering the document but leaves the `<head>` insertion points untouched; `generate_html` performs collection + insertion once rendering has fully settled. This covers generators registered mid-render (D1 makes later contexts correct; D2 makes the *current* context correct, e.g., dev-server first hit) and reactive styles created during async setup (`_reactive_styles` populated by then).
- `html_attrs` on the `<html>` element are still captured at document assembly (pre-render). Attributes set during render remain out of scope (theme applies them before render; no known consumer sets them mid-render).

**Alternatives considered**:
- *Two-pass render* (render once to discover, render again to emit): wasteful and side-effect-prone.
- *Collect after render but before `await_pending`*: misses async-setup reactive styles; rejected.

### D3: Per-context transfer state for server ports

**Decision**: Give each `ServerRenderContext` its own transfer-recording state by cloning the app-level prototype ports.

- `ServerResourcePort`: add a lightweight way to produce a fresh instance sharing the immutable config (`app_package_path`, `allow_list`) with an empty `_recorded`. `ServerRenderContext._register_ports()` provides the fresh instance instead of the shared one.
- `ServerFetchPort`: keep one configured app-level prototype (owns the external `httpx.AsyncClient` and ASGI configuration). Add `_clone_for_context()` (or equivalent) returning an instance that shares the external client and the saved `configure()` arguments but has a fresh `_response_cache`. The prototype stores its `configure()` arguments so clones can re-apply them (avoiding the "already configured" error and per-request ASGI client reuse issues are acceptable — `httpx.AsyncClient` over `ASGITransport` holds no sockets).
- `configure_server_context` keeps storing the prototypes on the app; no DI surface changes.

**Alternatives considered**:
- *Reset shared state at context creation*: racy under concurrent requests; rejected.
- *DI-provided per-context recorder objects that shared ports consult*: correct but adds DI keys and indirection through the fetch hot path; cloning is simpler and matches the isolation spec directly.

### D4: Opt-in full text-resource transfer (`resource_transfer = "used" | "all-text"`)

**Decision**: Add `resource_transfer: Literal["used", "all-text"] = "used"` to `WebComPyBuildConfig` (validated in `__post_init__`). When `"all-text"`, `generate_static_site()` reads every allow-listed **text** resource once and makes SSG embed that full map in every page's payload.

- Text classification by extension allowlist: `.md`, `.markdown`, `.txt`, `.json`, `.csv`, `.yaml`, `.yml`, `.toml`, `.svg`, `.html`, `.xml`. Binary allow-listed files are excluded.
- Size guard: log a warning when an individual file or the aggregate exceeds sane thresholds (e.g., 256 KB / 1 MB), but still include it — excluding would silently break the no-fetch guarantee.
- Plumbing: `generate_static_site()` computes the map and stashes it on the app (e.g., `app._ssg_full_text_resources`), following the existing `_server_fetch_port` prototype precedent; `collect_transfer_data()` unions it into `payload.resources` when present (per-context recorded entries still apply; union dedupes by path). Dev/prod serving never sets the stash, so serving behavior stays `"used"`.

**Alternatives considered**:
- *DI-provided mode + resource map*: cleaner separation but more wiring through context creation for an SSG-only concern; the app-attribute precedent already exists.
- *Transfer binary resources too*: payload bloat risk; excluded by design.

### D5: SSG preload covers the full route tree

**Decision**: In `generate_static_site()`, replace the flattened-`app.routes` preload loop with `app.router.preload_lazy_routes()` (which walks the page tree including parent/layout routes), keeping a fallback for routers without that method. With D1 this is defense-in-depth: it keeps imports scope-free and module side effects early.

### D6: `ResourcePort.preload(paths)` with browser fetch-cache priming

**Decision**: Add `async def preload(self, paths) -> None` to the `ResourcePort` ABC with a default no-op implementation; `BrowserResourcePort` overrides it.

- Browser behavior: for each path — validate; skip when present in the hydration payload (`RESOURCE_DATA_KEY`); otherwise call `FetchPort.fetch()` for the resource URL, populating the session `_response_cache` that `load_text`/`load_bytes` already consult via `_fetch_bytes()`. Individual failures are caught and logged (never raised).
- Server behavior: base-class no-op (does not touch `_recorded`).
- `docs_app` usage: after the root component mounts, schedule an idle (non-render) task that preloads every `source` in the docs manifest. With D4 enabled this is belt-and-braces (payload already covers those paths); it primarily benefits apps staying on `"used"`.

**Alternatives considered**:
- *A `use_prefetch_resources` composable*: nicer API discovery, but preload is a port capability used once per app; a port method is sufficient and composable-friendly later.
- *Prefetch on navigation intent (hover)*: better latency profile but doesn't compose into a guarantee; idle prefetch chosen for simplicity.

## Risks / Trade-offs

- **Registry growth** (`_all_component_generators` is append-only) → Generators are process-lifetime singletons by design; the list holds one reference per component, negligible.
- **Per-context `ServerFetchPort` clones create one ASGI `httpx.AsyncClient` per request** → No sockets involved (ASGITransport); overhead is trivial. External client is shared, not cloned.
- **D2 changes when `data-webcompy-dynamic` (theme) content is resolved** → Theme registers before render via deferred ops, so resolved content is unchanged; only late mutations (none known during SSR) would differ.
- **`all-text` payload growth** (docs_app: ~30 KB compressed per page) → Text-only filter + size warnings; opt-in, default unchanged.
- **Behavior change for existing SSG sites** (payloads shrink to per-context contents) → This is the bug fix itself; sites that depended on the accidental accumulation can opt into `"all-text"`.

## Migration Plan

No migration needed: all changes are additive or bug-fix-level behavioral corrections. Apps wanting the previous accidental behavior (all resources available after any entry page) enable `resource_transfer = "all-text"`.

## Open Questions

- Exact size-warning thresholds for `all-text` mode (defaults proposed above; tune during implementation).
- Whether `preload()` should also prime a future `BrowserResourcePort`-level memory cache instead of relying on the fetch cache (current design relies on the fetch cache; revisit if eviction semantics ever change).
