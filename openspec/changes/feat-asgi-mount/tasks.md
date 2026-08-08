# Tasks: feat-asgi-mount

## 1. Config surface

- [x] 1.1 Add `mounts: Callable[[], dict[str, ASGIApp]] | None = None` to `WebComPyServerConfig` (packages/webcompy-cli/src/webcompy_cli/config/_server_config.py), with an ASGI-app protocol type usable at type-check time without importing Starlette in the config module
- [x] 1.2 Verify `webcompy_config.py` import does not trigger mount callable invocation (lazy semantics test)

## 2. Route assembly

- [x] 2.1 In `create_asgi_app()` (packages/webcompy-cli/src/webcompy_cli/_server.py), invoke the mounts callable once and insert one Starlette `Mount` per entry immediately before the SSR catch-all route
- [x] 2.2 Implement collision detection: reject prefixes starting with `/_webcompy`, prefixes colliding with registered page routes, and prefixes that normalize to `/` (root mounting is rejected); raise `WebComPyException` listing all conflicts before serving
- [x] 2.3 Apply the same mount handling to the hash-mode serving path

## 3. SSG and fetch integration

- [x] 3.1 Verify/ensure `ServerFetchPort.configure()` receives the fully assembled app including mounts plus the configured mount prefixes, and add regression tests that mount paths are absent from `blocked_paths` and are dispatched without `base_url` prefixing under a non-root `base_url`
- [x] 3.2 Verify `generate_static_site()` with mounts configured: pages generated, mount endpoints reachable in-process during generation, no mount paths in `dist/`

## 4. Tests

- [x] 4.1 Unit test: mount insertion order (mount before catch-all; internal routes unaffected)
- [x] 4.2 Unit test: collision detection for reserved prefix and page-route conflicts
- [x] 4.3 Integration test (webcompy_testing ASGI client): a mounted Starlette/FastAPI-style app responds at `/api/...` while SSR pages still render
- [x] 4.4 Integration test: component self-site fetch to a mounted endpoint during SSR returns the mounted app's response and populates the transfer cache (including a non-root `base_url` case)
- [x] 4.5 Integration test: SSG with mounts completes; mounted fetch response is baked into hydration payload; `dist/` has no mount files

## 5. Verification

- [ ] 5.1 `uv run ruff check .`, `uv run ruff format --check .`, `uv run pyright`, `uv run python -m pytest tests/ --tb=short` all pass

## 6. Spec reference sync

- [ ] 6.1 Update AGENTS.md: verify the File→Spec Mapping entries for `webcompy_cli/` (`cli`, `project-config`, `ssg-via-ssr`) and `webcompy_server/ports/` (`server-fetch-asgi`) against the modified specs, and check the Framework Invariants list for fetch/mount-related staleness
- [ ] 6.2 Check `.opencode/skills/webcompy-review/SKILL.md` for stale assumptions about self-site fetch resolution and sync spec references
- [ ] 6.3 Run `python3 scripts/check-doc-spec-refs.py` and confirm it passes
