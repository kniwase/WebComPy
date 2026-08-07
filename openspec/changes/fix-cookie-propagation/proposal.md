# Proposal: fix-cookie-propagation

## Why

`ServerCookiePort` currently drops cookie attributes (`max_age`, `secure`, `samesite`, `httponly`, etc.) when `set()` is called during SSR — the cookie value is stored in internal state only and never reaches the browser. The `port-abstraction` spec already records this as a known limitation with a NOTE stating that attributes SHALL be propagated via `Set-Cookie` response headers once server-side functionality arrives. As WebComPy gains server-runtime capabilities (user-mounted ASGI apps, authentication-backed APIs), cookies set during SSR must be delivered to the browser with their attributes intact, or login/session flows silently break.

## What Changes

- `ServerCookiePort.set()` SHALL retain the full attribute set (`max_age`, `expires`, `path`, `domain`, `secure`, `httponly`, `samesite`) instead of discarding it.
- To carry the full attribute set, `CookiePort.set()` gains keyword-only `expires: datetime | None = None` and `domain: str | None = None` parameters (additive, backward compatible). `BrowserCookiePort.set()` SHALL apply them to `document.cookie` alongside the existing attributes; `ServerCookiePort.set()` SHALL retain them for `Set-Cookie` emission.
- Cookie writes performed during SSR SHALL be accumulated in the per-request `RenderContext` and emitted as `Set-Cookie` response headers on the HTML response produced by the dev/prod server.
- In hash-mode serving, the HTML shell is pre-rendered once and cached, so accumulated cookie writes SHALL NOT be emitted on hash-mode responses; this SHALL be documented as specified behavior.
- During SSG (`webcompy generate`), cookie writes SHALL be ignored (a static artifact cannot carry response headers); this SHALL be documented as specified behavior, not an error.
- No breaking changes: the read path (`get()`, `get_all()`, request `Cookie` parsing) is unchanged, and `set()` is extended additively (keyword-only parameters with `None` defaults) on both browser and server implementations.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `port-abstraction`: The "ServerCookiePort ignores Set-Cookie attributes" limitation is resolved. Cookie attribute propagation via `Set-Cookie` response headers during SSR becomes a requirement (upgrading the existing NOTE), and SSG-time behavior (ignore writes) is specified.

## Impact

- **Code**: `packages/webcompy/src/webcompy/ports/_cookie.py` (ABC extension), `packages/webcompy/src/webcompy/ports/_browser/_cookie.py` (browser attribute application), `packages/webcompy-server/src/webcompy_server/ports/_cookie.py` (attribute retention + pending-write accumulation), `packages/webcompy-server/src/webcompy_server/_context.py` (access to pending cookies from render context), `packages/webcompy-cli/src/webcompy_cli/_server.py` (`send_html` response header emission).
- **APIs**: Additive only: keyword-only `expires`/`domain` parameters added to `CookiePort.set()` (both `BrowserCookiePort` and `ServerCookiePort` accept them). Existing call sites are unaffected.
- **Dependencies**: None.
- **Specs**: `openspec/specs/port-abstraction/spec.md`.

## Known Issues Addressed

- Port abstraction: `ServerCookiePort` dropping `max_age`/`secure`/`samesite` attributes (documented in `port-abstraction` spec as a current limitation with a future-work NOTE).

## Non-goals

- Reading `Cookie` request headers beyond the existing `cookie_header` parsing (already supported).
- Cookie propagation for responses produced by user-mounted ASGI applications (those apps own their own response headers).
- Browser-side cookie attribute enforcement (delegated to the browser as today).
- Encrypted/signed cookie support.
