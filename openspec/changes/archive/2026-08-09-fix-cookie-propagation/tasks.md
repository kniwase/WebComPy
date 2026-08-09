# Tasks: fix-cookie-propagation

## 1. Cookie port attribute extension

- [x] 1.1 Add keyword-only `expires: datetime | None = None` and `domain: str | None = None` parameters to the `CookiePort.set()` ABC (packages/webcompy/src/webcompy/ports/_cookie.py)
- [x] 1.2 Apply `expires` (UTC date string) and `domain` in `BrowserCookiePort.set()` (packages/webcompy/src/webcompy/ports/_browser/_cookie.py) alongside the existing attributes

## 2. Server cookie port

- [x] 2.1 Extend `ServerCookiePort` (packages/webcompy-server/src/webcompy_server/ports/_cookie.py) to retain the full attribute set (`max_age`, `expires`, `path`, `domain`, `secure`, `httponly`, `samesite`) on `set()`, storing structured pending writes alongside the existing internal dict read path
- [x] 2.2 Add an accessor on `ServerCookiePort` (e.g. `get_pending_set_cookie_headers()`) that serializes pending writes to `Set-Cookie` header strings via `http.cookies.SimpleCookie` (server-only import; `expires` formatted to the RFC 1123 date string `Morsel` expects, `domain` assigned to the morsel) with last-write-wins per cookie name+path
- [x] 2.4 `ServerCookiePort.delete()` records an expiring pending write (`value=""`, `max_age=0`) so SSR deletions reach the browser via `Set-Cookie`

## 3. Response header emission

- [x] 3.1 In `send_html` (packages/webcompy-cli/src/webcompy_cli/_server.py), read pending `Set-Cookie` headers from the render context after `generate_html()` completes (before `ctx.dispose()`) and append them to the `HTMLResponse` as separate headers
- [x] 3.2 Ensure the hash-mode pre-rendered response path does NOT emit accumulated cookies

## 4. Tests

- [x] 4.1 Unit test: `ServerCookiePort.set()` with full attributes produces a correct `Set-Cookie` header string (Max-Age, Expires, Domain, Secure, HttpOnly, SameSite, Path preserved)
- [x] 4.2 Unit test: multiple cookie writes produce one header per cookie; last-write-wins for same name+path
- [x] 4.3 Unit test: values requiring quoting are serialized correctly
- [x] 4.4 Unit test: `BrowserCookiePort.set()` with `expires`/`domain` includes both attributes in the `document.cookie` write (via a browser test double)
- [x] 4.5 Integration test (webcompy_testing ASGI client): SSR response includes `Set-Cookie` headers set by a component during rendering
- [x] 4.6 Test: SSG (`generate_static_site`) completes without error when a component sets cookies, and static output is unaffected
- [x] 4.7 Test: hash-mode serving does not emit `Set-Cookie` headers for cookies set during the pre-render
- [x] 4.8 Unit test: `ServerCookiePort.delete()` produces a `Set-Cookie` header with `Max-Age=0` and removes the cookie from the read path

## 5. Verification

- [x] 5.1 `uv run ruff check .` and `uv run ruff format --check .` pass
- [x] 5.2 `uv run pyright` passes
- [x] 5.3 `uv run python -m pytest tests/ --tb=short` passes

## 6. Spec reference sync

- [x] 6.1 Update AGENTS.md: verify the File→Spec Mapping entries covering `webcompy/ports/` and `webcompy_server/ports/` against the modified `port-abstraction` spec, and check the Framework Invariants list for cookie-related staleness
- [x] 6.2 Check `.opencode/skills/webcompy-review/SKILL.md` for stale assumptions about `ServerCookiePort` attribute handling and sync spec references
- [x] 6.3 Run `python3 scripts/check-doc-spec-refs.py` and confirm it passes
