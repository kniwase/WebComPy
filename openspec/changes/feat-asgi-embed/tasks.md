# Tasks: feat-asgi-embed

## 1. Fetch port root binding

- [ ] 1.1 Add `root_app` parameter to `configure_server_context()` (packages/webcompy-server/src/webcompy_server/__init__.py) and thread it to `ServerFetchPort` configuration
- [ ] 1.2 Implement root-app binding in `ServerFetchPort` (packages/webcompy-server/src/webcompy_server/ports/_fetch.py): self-site dispatch against `root_app`; resolve the double-`configure()` interaction with the CLI (deferral or explicit rebind)
- [ ] 1.3 Adjust blocked-path evaluation for embedded mode: page paths prefixed by the mount prefix; host routes outside the prefix never blocked

## 2. Embedding support

- [ ] 2.1 Verify and fix asset/endpoint URL generation under a non-root `base_url` matching the mount prefix; in particular the `/_webcompy-resource` route is registered with the `base_url` prefix inside the app (`_server.py`) while the browser URL builder also prefixes `base_url` (`ports/_browser/_resource.py`) — under a mount this double-prefixes; adjust embedded-mode route construction while keeping standalone behavior unchanged (per design D5)
- [ ] 2.2 Verify hash-mode serving under a mount prefix

## 3. Tests

- [ ] 3.1 Integration test: host Starlette/FastAPI app with `mount("/admin", serving.asgi)` — SSR page render, framework endpoints under prefix, host routes unaffected
- [ ] 3.2 Integration test: embedded component self-site fetches a host API route during SSR via ASGI transport; response recorded in transfer cache
- [ ] 3.3 Test: blocked-path behavior — `/admin/<page>` blocked, host `/api/...` fetchable
- [ ] 3.4 Test: default (`root_app=None`) behavior byte-identical to before

## 4. Docs and verification

- [ ] 4.1 Docs + minimal example project: embedding WebComPy as an admin UI inside an existing FastAPI app, including the required `base_url`/mount-prefix pairing and the note that the host owns the server process (per `doc-spec-references`: docs reference the owning specs as source of truth rather than transcribing requirement prose)
- [ ] 4.2 `uv run ruff check .`, `uv run ruff format --check .`, `uv run pyright`, `uv run python -m pytest tests/ --tb=short` all pass

## 5. Spec reference sync

- [ ] 5.1 Update AGENTS.md: add `asgi-embed` to the Current Specs list; add File→Spec Mapping entries for `webcompy_server/__init__.py` (`configure_server_context` → `asgi-embed/spec.md`) and the modified `server-fetch-asgi` rows
- [ ] 5.2 Check `.opencode/skills/webcompy-review/SKILL.md` for stale assumptions and sync invariant headings/spec references
- [ ] 5.3 Run `python3 scripts/check-doc-spec-refs.py` and confirm it passes
