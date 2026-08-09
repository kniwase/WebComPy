# Tasks: feat-asgi-embed

## 1. Fetch port root binding

- [x] 1.1 Add `root_app` parameter to `configure_server_context()` (packages/webcompy-server/src/webcompy_server/__init__.py) and thread it to `ServerFetchPort` configuration
- [x] 1.2 Implement root-app binding in `ServerFetchPort` (packages/webcompy-server/src/webcompy_server/ports/_fetch.py): self-site dispatch against `root_app`; resolve the double-`configure()` interaction with the CLI (deferral or explicit rebind)
- [x] 1.3 Adjust blocked-path evaluation for embedded mode: page paths prefixed by the mount prefix; host routes outside the prefix never blocked

## 2. Embedding support

- [x] 2.1 Verify and fix asset/endpoint URL generation under a non-root `base_url` matching the mount prefix; in particular the `/_webcompy-resource` route is registered with the `base_url` prefix inside the app (`_server.py`) while the browser URL builder also prefixes `base_url` (`ports/_browser/_resource.py`) — under a mount this double-prefixes; adjust embedded-mode route construction while keeping standalone behavior unchanged (per design D5)
- [x] 2.2 Verify hash-mode serving under a mount prefix

## 3. Tests

- [x] 3.1 Integration test: host Starlette/FastAPI app with `mount("/admin", serving.asgi)` — SSR page render, framework endpoints under prefix, host routes unaffected
- [x] 3.2 Integration test: embedded component self-site fetches a host API route during SSR via ASGI transport; response recorded in transfer cache
- [x] 3.3 Test: blocked-path behavior — `/admin/<page>` blocked, host `/api/...` fetchable
- [x] 3.4 Test: default (`root_app=None`) behavior byte-identical to before

## 4. Verification

- [x] 4.1 `uv run ruff check .`, `uv run ruff format --check .`, `uv run pyright`, `uv run python -m pytest tests/ --tb=short` all pass

## 5. Spec reference sync

- [x] 5.1 Update AGENTS.md: add `asgi-embed` to the Current Specs list; add File→Spec Mapping entries for `webcompy_server/__init__.py` (`configure_server_context` → `asgi-embed/spec.md`) and the modified `server-fetch-asgi` rows
- [x] 5.2 Check `.opencode/skills/webcompy-review/SKILL.md` for stale assumptions and sync invariant headings/spec references
- [x] 5.3 Run `python3 scripts/check-doc-spec-refs.py` and confirm it passes
