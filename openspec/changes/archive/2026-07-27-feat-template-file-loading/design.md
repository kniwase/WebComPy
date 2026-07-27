## Context

Change 1 established `render_template(source: str, context)` as the public template engine entry point. The original Change 4 design proposed extending this to accept `pathlib.Path`, using `Path.read_text(encoding="utf-8")` on the server and raising `WebComPyException` on the browser. That design was rejected because:

- After SSR hydration, any client-side route navigation re-runs the component's `setup()` function and re-invokes `render_template(Path("templates/card.html"))`. In the PyScript environment there is no way to read a file from the developer's filesystem, so every CSR navigation that touched a path-based template would crash.
- A follow-up investigation explored routing through the existing `load_asset` mechanism (`webcompy.assets`), which is the framework's official way to bundle non-Python files into the wheel. This also failed: `load_asset` reads from `app._assets_registry`, a module generated only at wheel-build time. SSR runs in the same Python interpreter as the dev/prod server, where the application package is loaded from source — not from a wheel — and `_assets_registry.py` does not exist on disk. `load_asset` would raise `AssetNotFoundError` on the server.
- Both options also failed to address the deeper deployment question: how does each environment (SSG-static-host, SSR-live-server, PyScript-direct) obtain resource bytes at runtime?

Three pieces of existing infrastructure have converged to make a cleaner design possible:

1. **Async component setup** (`async-component-setup/spec.md`): components can be `async def` and `await` arbitrary operations before returning the rendered tree. Suspense boundaries show fallback UI during the await.
2. **A unified `FetchPort`**: the framework already ships browser (`BrowserFetchPort`) and server (`ServerFetchPort`) implementations of an async HTTP fetch abstraction. The browser port is synchronous enough for the main-thread PyScript runtime to be effectively async-only; the server port wraps httpx.
3. **An existing hydration payload** (`hydration-data-transfer/spec.md`): a `<script type="application/json" id="__webcompy_data__">` blob already transports server-side fetch caches and resolved `AsyncResult` states to the browser at hydration time. Adding a `resources` slot to this blob is straightforward.

These three together make the obvious design possible: components load resources explicitly via an async `ResourcePort`, the browser fetches over HTTP from a server endpoint, and the SSR pass pre-populates the hydration payload so the browser doesn't refetch on hydration. The template engine itself stays `str`-only and does not need to know about paths.

## Goals / Non-Goals

**Goals:**
- Provide an async `ResourcePort` interface that, given a package-relative resource path, returns its UTF-8 text or raw bytes content
- Make file-based templates work in any deployment mode without changing `render_template`'s public signature
- Eliminate the duplicate network round-trip on hydration by embedding resources loaded during SSR into the hydration payload
- Auto-detect resource files by default patterns (`**/*.html`, `**/*.css`, `**/*.md`, `**/*.svg`, `**/*.txt`) so users don't declare each file individually, with `resources` / `resource_exclude` overrides
- Replace the existing `load_asset` API with a port-based mechanism that doesn't hardcode the app package name and supports the full set of consumers (templates, CSS text, Markdown, raw bytes for images/fonts)
- Eliminate the dev-time restart requirement by reading from the live server (no wheel rebuild needed)

**Non-Goals:**
- `render_template(Path)` overload — keeping the template engine `str`-only avoids an async/sync split and preserves single-responsibility
- Sync `load_text` / `load_bytes` — async-only collapses the previous sync/async compatibility surface
- Wheel bundling of resource files — replaced by the endpoint + SSG static-copy strategy
- `load_asset` compatibility shim — removed entirely; no internal consumers remain
- Browser-side fetch caching — deferred; freshness on every fetch keeps dev iteration simple
- Resource file watching or hot-replacement — uvicorn's `.html` reload (and equivalent for other extensions) is out of scope; server-side reads are already fresh
- `use_template` / `use_resource` composables — `load_text` / `load_bytes` are plain async helper functions, not stateful composables

## Decisions

### D1: `ResourcePort` is async-only with `load_text` and `load_bytes`; `render_template` stays `str`-only

`ResourcePort` declares two methods:
```python
async def load_text(self, path: str) -> str: ...
async def load_bytes(self, path: str) -> bytes: ...
```

Template authors and other consumers do not pass `Path` into `render_template`. They call `webcompy.load_text(path)` (or `load_bytes`) inside an async component setup, receive the string, and pass that string to `render_template`. This decouples file loading from the template engine and keeps `render_template` a pure, sync, str-only parser.

**Rationale — why async-only?** With `async-component-setup` already in place, the sync/async split problem dissolves: file templates simply require an `async def` setup. Collapsing both `load_text` and `load_bytes` to async eliminates the dichotomy that the previous proposals (sync filesystem read on server + sync wheel-read on browser) had to engineer around. There is exactly one async method signature and one code path.

**Rationale — why keep `render_template(str, ctx)` unchanged?** Changing the signature to accept `Path` would mean either:
- (a) keeping `render_template` sync and raising on browser `Path` arguments (broken in CSR), or
- (b) making `render_template` async and propagating async through component setup everywhere it is called (large ripple).

Option (a) is what the original Change 4 tried and what the user rejected. Option (b) makes every template-using component async, including those with inline strings that don't need it. By hoisting the path-to-string resolution to user code, `render_template` keeps its sync, str-only contract, and async is opt-in for components that actually need it.

**Rationale — why both `load_text` and `load_bytes`?** Templates, CSS, and Markdown are text and need `str`. Images, fonts, and arbitrary binary assets need `bytes`. Both are bundled by the auto-detection rules and served by the same endpoint; the browser's `FetchPort` already returns a `Response` with both text and binary accessors.

### D2: Browser fetches from a server endpoint; same URL convention in SSR, SSG, and PyScript-direct

The browser implementation does this lookup chain:
1. Check the hydration payload (`RESOURCE_DATA_KEY`). If the path is present, return its decoded content immediately.
2. Otherwise, fetch `GET {base_url}_webcompy-resource/{path}` via the existing `FetchPort`. On success, return the response text or bytes.

The URL convention is identical across deployment modes. The backing store behind the URL differs:
- **Dev/prod SSR** (`webcompy start`): a Starlette route in `create_asgi_app` reads the file fresh from the application package directory on every request and returns it with the appropriate `Content-Type`.
- **SSG static host** (`webcompy generate`): `generate_static_site` copies allow-listed resources to `dist/_webcompy-resource/{path}` as static files; the host serves them as ordinary files at the same URL.
- **PyScript-direct on a static host**: same as SSG.

**Rationale — why one URL serves both live and static hosting?** A static host doesn't care whether the file was placed there manually by `generate_static_site` or is served dynamically by uvicorn — both look like ordinary HTTP file responses. The browser port doesn't need to know which mode it's in; it just fetches the URL and uses whatever returns. This eliminates mode flags, dual registries, and conditional code paths.

**Rationale — why no wheel bundling?** Wheel bundling forces a wheel rebuild to change resource contents in the browser, which means hot-reload is impossible without either (a) wheel rebuild on file change (slow) or (b) a parallel fetch fallback (the abandoned wheel-with-fetch design). The endpoint model gives the browser the same freshness as the server gets from `Path.read_text()` on every call, naturally.

### D3: Resources loaded during SSR are embedded in the hydration payload, eliminating the duplicate fetch on hydration

`ServerResourcePort` tracks `(path, content_bytes)` for every successful read during a `RenderContext`'s lifetime. At SSR/SSG payload generation time, this record is serialized into the `TransferPayload.resources` field (base64-encoded for transport safety, decoded by the browser port on hydration). `BrowserResourcePort` reads `RESOURCE_DATA_KEY` from the DI scope and consults it before issuing any fetch.

The transfer bumps `TransferPayload.__webcompy_transfer_version__` from `2` to `3`. Version negotiation handles hydration payloads from prior versions (no `resources` key) by treating the embedded slot as empty.

**Rationale — why embed?** Without embedding, every page with a path-template component would re-fetch the template on hydration, despite the server having already resolved it during SSR. That's wasted bandwidth, an extra round trip before interactivity, and a visible flash if the fetch is slow.

**Rationale — why in the existing hydration payload?** The `<script type="application/json" id="__webcompy_data__">` blob already transports `TransferPayload` fields. Adding `resources` is a one-line schema change plus the codec path used by every other field. It composes with the existing `transfer-codec/spec.md` (Signal types, datetime, etc.) and the existing `payload-compression/spec.md` threshold-based gzip. No new transport mechanism is introduced.

**Rationale — why no separate payload?** Resources are conceptually a subset of "what the SSR pass already computed" — the same category as fetch caches and resolved AsyncResult states. Splitting them into a separate payload would duplicate the codec, the rendering placement in `generate_html`, and the version negotiation.

**Tradeoff — payload size grows**: templates and CSS bundled into the payload inflate the initial HTML download. The existing `compression_threshold` mechanism applies identically. For typical pages this is negligible; for pages with very large embedded resources, the optimizer path (extracting large payloads to a separate file, deferring fetch) is a separate change.

### D4: Resource paths are package-relative POSIX strings, identical on server and browser

`ResourcePort.load_text(path)` accepts a package-relative POSIX path: forward slashes, no leading slash, no `..` segments. Examples:
- `templates/card.html`
- `components/widgets/header.css`
- `assets/icons/star.svg`

Both `ServerResourcePort` and `BrowserResourcePort` resolve paths against the application package root:
- **Server** uses `app._server_resource_port: ServerResourcePort | None`, set by `configure_server_context(app, *, resource_port: ServerResourcePort | None = None)` in `webcompy_server/__init__.py` (mirrors the existing `app._server_fetch_port` assignment). The CLI constructs `ServerResourcePort(app_package_path, allow_list)` in `resolve_build_artifacts` (it has both pieces of information in scope) and passes the fully-built instance into `configure_server_context`. `ServerRenderContext._register_ports` simply reads `app._server_resource_port` and provides it via `RESOURCE_PORT_KEY` when non-`None`. Containment and allow-list checks live inside the port. Tests that don't pass `resource_port` keep `app._server_resource_port = None`; `_register_ports` then skips the provide and `inject(RESOURCE_PORT_KEY, default=None)` returns `None` — a clean error path for tests that don't exercise resources.
- **Browser** looks up `path` in the hydration payload or fetches `{base_url}_webcompy-resource/{path}`. The path is opaque to the browser; it is the server endpoint's responsibility to validate and serve.

**Rejected — caller-relative path resolution**: `inspect.stack()` against the calling module's `__file__`. Rejected because `__file__` differs between source tree and wheel-installed bytecode paths, and wheel extraction in PyScript assigns `__file__` paths with no meaningful correspondence to source. A separate helper for caller-relative resolution could be added later if desired, but it complicates security (must still be validated against the port's `app_package_path`) and is not needed for common use cases.

**Rejected — absolute paths**: tying the API to absolute paths breaks wheel relocation and static-host deployment.

### D5: Resource files are auto-detected by pattern, with `BuildConfig` overrides; allow-list enforced at the endpoint

The CLI computes the allow-list once at startup: walk `app_package_path`, match include patterns, subtract exclude patterns. The result drives three things:
- the server endpoint's allow-list (rejects requests outside the set)
- the SSG copy step's file list
- (unused) anything else — the wheel does not contain the resources

Default include patterns: `**/*.html`, `**/*.css`, `**/*.md`, `**/*.svg`, `**/*.txt`. Default excludes: the build's existing skip patterns for `__pycache__`, `.git`, `.webcompy_modules`, etc.

Overrides via `WebComPyBuildConfig`:
- `resources: list[str] | None = None` — additional glob patterns to include beyond the defaults. Pass `[]` to disable auto-detection entirely (only explicit allowlisted assets, if any remain, are served).
- `resource_exclude: list[str] | None = None` — glob patterns to exclude from the auto-detected set.

**Rationale — defaults are conservative**: the defaults cover common web assets without pulling in arbitrary file types. Users wanting images or fonts (`**/*.png`, `**/*.woff2`) opt in via `resources=...`. This avoids accidental wheel/disk bloat from a stray `.log` or `.tmp` file.

**Rationale — `[]` to disable, not `False`**: semantic clarity. `None` means "use defaults" (the most common case). `[]` means "no auto-detection". Empty list is unambiguous; relying on `False`/`True` is not Python-idiomatic.

**Rationale — endpoint allow-list enforcement**: even with auto-detection working correctly, the endpoint must not serve arbitrary files (e.g., `webcompy_config.py` containing secrets, `.env`, `.git/`). The allow-list is the canonical set of "these are resources I want served"; the endpoint uses `realpath` containment to reject paths that resolve outside `app_package_path`.

### D6: The legacy `load_asset` API, the `assets` field, and `_assets_registry` are removed

The existing `webcompy.assets.load_asset` (sync, wheel-only, hardcoded to `app._assets_registry`), the `WebComPyBuildConfig.assets` field, the `_generate_assets_registry` wheel-builder helper, and the runtime presence of `app._assets_registry` modules are all removed in this change.

**Rationale — supersession**: the new `ResourcePort` covers everything `load_asset` did plus much more:
- sync → async, broadening use cases (fetch-based lazy loading, future async streaming)
- wheel-only → fetch + payload embedding, covering all deployment modes
- hardcoded `app.` lookup → DI-based discovery, working with any app package name
- bytes-only → text and bytes
- assets field → auto-detected files + `resources` overrides

There are no remaining internal consumers of `load_asset`. External consumers must migrate to `load_text` / `load_bytes` from `webcompy.resources`.

**Rationale — no deprecation cycle**: the cost of carrying two implementations through a release cycle outweighs the cost of a single breaking change for users with negligible usage. The transition target is unambiguous (`load_text(keyword)` ↔ `load_asset(keyword)`) and the framework itself has no `load_asset` callers to migrate.

## Risks / Trade-offs

- **[Risk] Hydration payload size grows with embedded resources** → Mitigation: existing `compression_threshold` (default 1024 bytes) gzips the payload above the threshold. Pathological cases (large inlined CSS bundles per page) can be deferred to ETag-based separate-file serving in a future change.
- **[Risk] Auto-detection picks up unintended files in user projects** → Mitigation: defaults are conservative text/image patterns; `resource_exclude` allows per-project filtering; a startup log line reports the detected count for review.
- **[Risk] Endpoint serves path-traversed resources** → Mitigation: `realpath` containment check inside `ServerResourcePort` (validated against its configured `app_package_path`) and inside the endpoint handler (validated against `build_config.app_package_path`); absolute paths and `..` segments are rejected before any filesystem access.
- **[Risk] Endpoint accidentally serves `webcompy_config.py` or `.env`** → Mitigation: allow-list enforcement; only auto-detected / declared paths are servable.
- **[Risk] SSR endpoint becomes a CSRF / SSRF surface** → Mitigation: in production, deployment is responsible for exposing the endpoint only as needed; for the dev server, the endpoint is same-origin by definition. SSG static copies reduce surface area (no live endpoint).
- **[Risk] `importlib.resources`-style fallback in browser is not used** → Note: with no wheel bundling, the browser port has no fallback to `importlib.resources`. The hydration payload is the only source before the network fetch. If neither has the resource, `ResourceNotFoundError` is raised. This is a clean error path; no silent failures.
- **[Risk] `async def` setup is mandatory for components using `load_text`** → Acknowledged. Documented in `resource-port/spec.md`. Inline-string components (`render_template(str, ctx)`) remain sync and unaffected.
- **[Tradeoff] Hydration payload version bumps to 3** → Addressed via the existing version negotiation in `deserialize_payload`. Version-2 payloads still parse; the missing `resources` key defaults to empty, and the browser fetches on demand.
- **[Tradeoff] `assets` field users have no migration shim** → Acknowledged as part of breaking change. No internal consumers; external migration is one-line.

## Open Questions

None — all design decisions resolved during planning phase. Two follow-up changes are anticipated but out of scope for this change:

1. **`CompressionThreshold` for embedded resources** — resource bytes inside the hydration payload don't get the same threshold-based gzip that text fields do; tighter tuning for the `resources` slot specifically is a future enhancement.
2. **ETag / `If-None-Match` on the resource endpoint** — would enable 304 responses for unchanged resources across page loads in production. Currently every fetch returns 200 with full content.
