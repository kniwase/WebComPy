# Design: fix-cookie-propagation

## Context

`ServerCookiePort` (packages/webcompy-server/src/webcompy_server/ports/_cookie.py) currently stores only name/value pairs in an internal dict; all attributes passed to `set()` are discarded. The `CookiePort.set()` ABC accepts `max_age`, `path`, `secure`, `httponly`, and `samesite`, but has no `expires` or `domain` parameters. The `port-abstraction` spec documents this as a known limitation and notes that attributes must eventually propagate via `Set-Cookie` response headers. The HTML response for SSR pages is assembled in `send_html` (packages/webcompy-cli/src/webcompy_cli/_server.py), which builds a Starlette `HTMLResponse` after rendering via a per-request `ServerRenderContext`. The render context is created per request (`app.create_render_context(path, cookie_header=...)`) and disposed in `finally`, so it is the natural per-request carrier for pending cookie writes.

## Goals / Non-Goals

**Goals:**
- Preserve the full attribute set on `ServerCookiePort.set()`.
- Emit accumulated cookie writes as `Set-Cookie` headers on the SSR HTML response.
- Keep per-request isolation (no cross-request leakage).
- Specify SSG behavior: writes ignored, no error.

**Non-Goals:**
- Cookies on responses from user-mounted ASGI apps (out of scope; those apps own their responses).
- Signed/encrypted cookies.
- Changes to the browser-side `CookiePort`.

## Decisions

### D1: Accumulate pending writes in the render context, not the port
`ServerCookiePort` is provided per render context via DI (`ServerRenderContext._register_ports()`). The port holds a small mutable list of pending `Set-Cookie` header strings (or structured records). `send_html` reads them from the context after `generate_html()` completes and before `ctx.dispose()`.

**Why**: The port is the natural write interception point (component code calls `CookiePort.set()`), while the response assembly lives in the CLI layer. The render context is the only object both sides share. Alternatives considered: (a) returning cookies from `generate_html()` — rejected because it changes the html-generator contract for one concern; (b) a module-level collector — rejected (violates the no-new-globals invariant and breaks per-request isolation).

### D2: Header emission point is `send_html` in `_server.py`
Both history-mode and hash-mode SSR responses pass through `send_html` / its hash-mode counterpart. Hash mode renders once at startup into a cache, so cookies written there have no per-request meaning; hash-mode responses SHALL NOT emit accumulated cookies (documented behavior). Only the per-request history-mode path emits `Set-Cookie` headers.

**Why**: Hash-mode serving is a static-style deployment; cookies set at startup render would leak across all requests.

### D3: Attribute serialization uses Python stdlib `http.cookies.SimpleCookie`
Build the `Set-Cookie` header value via `http.cookies` (`Morsel` handles `max-age`/`expires`/`path`/`domain`/`secure`/`httponly`/`samesite` formatting and quoting correctly). `expires` (a `datetime`) is formatted to the RFC 1123 date string `Morsel` expects; `domain` is assigned to the morsel's `domain` key. Multiple cookies → multiple `Set-Cookie` headers (Starlette `response.headers.append` / raw header list), since `Set-Cookie` must not be comma-joined.

**Why**: Hand-rolling cookie serialization is error-prone (quoting, date format); stdlib is correct and adds no dependency. Note: `SimpleCookie` is server-only code — never imported in browser paths.

### D4: SSG ignores writes silently
`generate_static_site` fetches pages through the same ASGI app; `send_html` will emit headers during generation too, but httpx response headers are simply not persisted to the static file — no special-casing needed in the SSG layer. The spec requirement ("ignored, not an error") is satisfied by construction.

### D5: `CookiePort.set()` gains keyword-only `expires` and `domain` parameters
The attribute-retention requirement includes `expires` and `domain`, which the current ABC does not accept. Both are added as keyword-only parameters with `None` defaults (additive, backward compatible). `BrowserCookiePort.set()` applies them to `document.cookie` (`expires` formatted as a UTC date string, `domain` as-is), matching the existing attribute handling; `ServerCookiePort` retains them and serializes them via `Morsel` (D3).

**Why**: `domain` is required for real cross-subdomain session cookies and `expires` for absolute-expiry cookies; both are natively supported by `document.cookie` and `http.cookies`, so the parity cost is minimal. Alternative considered: restrict the spec to the five attributes the ABC accepts today — rejected because it would leave the port unable to express common cookie configurations, and because the extension is purely additive (no existing call site is affected).

## Risks / Trade-offs

- [Attribute values with non-ASCII or control characters could produce malformed headers] → `http.cookies` performs quoting; add a test with values requiring quoting.
- [A component setting many cookies inflates response headers] → Acceptable; bounded by typical session usage. No dedup beyond last-write-wins per cookie name (matching browser semantics: later `Set-Cookie` for the same name+path overwrites).
- [Hash-mode users expect cookies to work] → Documented as unsupported; hash mode is static-style serving.

## Migration Plan

No migration. Existing behavior (attributes dropped) was undocumented for users; the change only adds headers that were previously absent.

## Open Questions

- None.
