# Fetch Middleware

## Purpose

Stackable request/response processors around `FetchPort` that let applications and plugins intercept HTTP operations (auth headers, logging, retries) and synthesize responses without replacing the port — preserving hydration-cache semantics, blocked-path guards, and streaming behavior. Interception is also the foundation for browser-side mocks that run without a server.

## Requirements

### Requirement: FetchMiddleware shall wrap fetch and stream with a next function

`FetchMiddleware` SHALL be an async callable receiving a request object exposing `url: str`, `method: str`, `headers: dict[str, str] | None`, and `body: str | bytes | None`, plus a `next` function. Calling `await next(request)` SHALL invoke the next layer (the following middleware, or the concrete `FetchPort`). The middleware SHALL return a `Response` (for `fetch`) or a `FetchStream` (for `stream`). Middleware SHALL be applicable to both `fetch` and `stream` paths of `FetchPort`.

#### Scenario: Pass-through middleware

- **WHEN** a middleware calls `await next(request)` unchanged and returns its result
- **THEN** the request reaches the inner layers and the response is returned unmodified

#### Scenario: Request mutation before next

- **WHEN** a middleware mutates `request.headers` (e.g. adds `Authorization`) before calling `next(request)`
- **THEN** the inner layers receive the mutated headers

### Requirement: Interception shall short-circuit via next without losing downstream processing

A middleware MAY intercept by returning without calling `next`. Alternatively it MAY call `next(request, response=synthetic_response)` (or `response=synthetic_stream` on the streaming path), which SHALL skip the inner port while still returning the supplied object through the normal chain exit. Synthetic responses at this layer do not bypass any higher-level processing: RPC callers SHALL still parse and validate the synthetic body, and HttpClient callers SHALL receive it as a normal `Response`.

#### Scenario: Interceptor returns a synthetic response

- **WHEN** a middleware matches a URL pattern and returns a constructed `Response` without calling `next`
- **THEN** no network request is issued and the caller receives the synthetic response

#### Scenario: Short-circuit via next(response=...)

- **WHEN** a middleware calls `next(request, response=Response(text="{}"))`
- **THEN** the inner port's fetch is not invoked and the synthetic response flows back through remaining outer middleware

### Requirement: Chain order shall place middlewares[0] outermost

The registered middleware list SHALL compose such that `middlewares[0]` is the outermost layer — first to observe the request and last to observe the response — implemented by wrapping in reversed list order around the concrete port. This ordering SHALL hold regardless of registration source (registry, plugin hook, utility).

#### Scenario: Declaration order equals execution order

- **WHEN** middlewares `[a, b, c]` are registered
- **THEN** a request passes through `a`, then `b`, then `c`, then the concrete port; responses flow back through `c`, `b`, `a`

### Requirement: Registries shall provide additive registration via DI

`FETCH_MIDDLEWARE_KEY` SHALL resolve to a fresh per-render-context registry object exposing `use(middleware)` for append-style registration and a read-only ordered view of registered middlewares. Because DI `provide` overwrites, distributed additions SHALL go through the registry rather than providing replacement lists. Utility functions (`add_fetch_middleware(mw)`) SHALL inject the active registry and delegate to `use`.

#### Scenario: Additions from multiple sources accumulate

- **WHEN** a plugin hook registers middleware `a` and application code later calls the registry's `use(b)`
- **THEN** the chain contains both `a` and `b` in registration order

#### Scenario: Fresh registry per render context

- **WHEN** a new render context is created (new SSR request or browser boot)
- **THEN** its registry starts empty unless populated during that context's initialization

### Requirement: Plugin hooks shall aggregate middleware in declaration order

`WebComPyPlugin.get_fetch_middlewares()` SHALL return an optional list of middlewares. `PluginManager` SHALL concatenate results across plugins in `AppConfig.plugins` declaration order and register each on the fetch middleware registry before chain assembly.

#### Scenario: Plugin-provided interceptor participates in ordering

- **WHEN** two plugins declare fetch middlewares and are listed in order `[first, second]`
- **THEN** `first`'s middleware is registered before `second`'s and therefore sits outermost relative to it

### Requirement: Streaming middleware shall resolve at header-commit time

On the streaming path, `next` SHALL resolve to a `FetchStream` once status and headers are committed and before any body chunk is consumed, allowing middleware to inspect headers or substitute a stream. Synthetic streams SHALL be supported; downstream chunk consumers remain unaware of substitution.

#### Scenario: Header inspection before body consumption

- **WHEN** a middleware awaits `next(request)` on a streaming request
- **THEN** the returned stream exposes `status_code`, `headers`, and `ok` immediately, with iteration deferred until the caller consumes it

### Requirement: The wrapper shall delegate port internals to the innermost port

The middleware chain wrapper SHALL delegate `populate_from_transfer`, `get_transfer_data`, `clear_cache`, `close`, `is_self_site_url`, and the server-side `noop` marker to the wrapped port so hydration transfer, blocked-path recursion guards, and SSE degradation behave identically with or without middleware.

#### Scenario: Hydration cache survives middleware

- **WHEN** a hydration payload seeds responses via `populate_from_transfer` on a wrapped port
- **THEN** subsequent matching fetches hit the seeded cache through the chain

#### Scenario: Blocked-path guard not bypassed

- **WHEN** middleware passes a blocked self-site page route through `next`
- **THEN** the inner `ServerFetchPort` still applies its blocked-path guard
