# Tasks: feat-fetch-rpc-middleware

## 1. Fetch Middleware Foundation

- [ ] 1.1 Define `FetchMiddleware` type, request view object (`url`/`method`/`headers`/`body`), and `FetchMiddlewareRegistry` (additive `use()`, ordered read-only view) in `packages/webcompy/src/webcompy/ports/_fetch.py`; add `FETCH_MIDDLEWARE_KEY` to `ports/_keys.py`
- [ ] 1.2 Implement `_MiddlewareFetchPort(FetchPort)` wrapping `fetch` and `stream` with reversed-order chain composition; delegate `populate_from_transfer`, `get_transfer_data`, `clear_cache`, `close`, `is_self_site_url`, `noop`
- [ ] 1.3 Support the interceptor paths: return-without-`next` and `next(request, response=...)` / stream equivalent
- [ ] 1.4 Add unit tests: pass-through, request mutation, ordering (`[a,b,c]` → a→b→c→port), interception, synthetic response via `next(response=...)`

## 2. RPC Middleware Foundation

- [ ] 2.1 Define `RpcMiddleware` type and context (`method`/`params`/mutable `headers`/`result_type`, batch metadata), plus `RpcMiddlewareRegistry`; add `RPC_MIDDLEWARE_KEY`
- [ ] 2.2 Thread per-call headers through `_call_impl` / `_notify_impl` / batch HTTP path / `_stream_impl` in `rpc/_client.py`, merging onto fixed headers with `Content-Type` forced to `application/json`
- [ ] 2.3 Implement validated short-circuit: `next(ctx, response={"result":..., "meta":...})` routes through `_resolve_single`; streaming variant routes items through `_decode_stream_item`
- [ ] 2.4 Add unit tests: typed params visibility, header merge/clobber-protection, selective scoping by `ctx.method`, batch-level middleware invocation, mocked result validation, malformed synthesis raising `RpcError`, SSE stream substitution with item decoding preserved

## 3. Assembly and Plugin Hooks

- [ ] 3.1 Create fresh registries in both `BrowserRenderContext._register_ports` and `ServerRenderContext._register_ports` (`webcompy_server/_context.py`)
- [ ] 3.2 Add `get_fetch_middlewares()` / `get_rpc_middlewares()` default-empty hooks to `WebComPyPlugin`; aggregate in declaration order in `PluginManager.init_render_context` onto the registries
- [ ] 3.3 Assemble chains after plugin initialization in `RenderContext.__init__`: wrap `FETCH_PORT_KEY` (and resolve RPC registry wrapping) only when middlewares are non-empty; re-provide keys
- [ ] 3.4 Add tests: zero-middleware fast path returns unwrapped port, plugin hook order matches `AppConfig.plugins` order, hydration cache seeded through wrapper, blocked-path guard intact under middleware

## 4. Utilities and Exports

- [ ] 4.1 Add `add_fetch_middleware(mw)` / `add_rpc_middleware(mw)` delegating to the active context's registries; export types, registries, keys, utilities from public entry points (`webcompy.ports`, `webcompy.rpc`, `webcompy.plugin`) with `.pyi` updates
- [ ] 4.2 Write Google-style docstrings for all new public interfaces (checker-strict); run `python3 scripts/check-docstrings.py` and pydoclint

## 5. Sample Plugins and E2E

- [ ] 5.1 Create sample plugins used by tests/demo: URL-pattern fetch interceptor plugin and procedure-mocking RPC plugin (browser-runnable, no server)
- [ ] 5.2 Add E2E scenario exercising a mocked RPC call inside a PyScript page without an RPC server route registered, asserting identical behavior on prod and static serving modes

## 6. Verification

- [ ] 6.1 Run `uv run ruff check .` and `uv run ruff format --check .`
- [ ] 6.2 Run `uv run pyright`
- [ ] 6.3 Run `uv run python -m pytest tests/ --tb=short` — full suite green including existing ajax/rpc/plugin suites
- [ ] 6.4 Update `AGENTS.md` File → Spec Mapping (`webcompy/ports/`, `webcompy/ajax/`, `webcompy/rpc/`, `webcompy/plugin/` rows gain `fetch-middleware`/`rpc-middleware`), Framework Invariants if needed, Current Specs list; sync `.opencode/skills/webcompy-review/SKILL.md`; run `python3 scripts/check-doc-spec-refs.py`
- [ ] 6.5 Run `openspec validate feat-fetch-rpc-middleware`
