# Tasks: feat-docs-server-tooling

## 1. Pages

- [ ] 1.1 Write `server_cli_reference.md` (subcommand tables + worked examples for start/generate/init/lock/inspect) + wrapper + manifest; add parser-vs-docs unit test
- [ ] 1.2 Write `server_project_configuration.md` (two-file model, field guide for build/server configs, resource allow-list, lockfile lifecycle) + wrapper + manifest
- [ ] 1.3 Write `server_asgi_integration.md` (embed-in-host incl. base_url/blocked-paths semantics; mounts under WebComPy; SSG interaction) + wrapper + manifest
- [ ] 1.4 Write `server_serving_modes.md` (CDN/local runtime+wasm, standalone, wheel modes, `.webcompy_modules/`, offline checklist) + wrapper + manifest
- [ ] 1.5 Write `server_testing.md` (TestRenderer, fake ports inventory, ASGI helpers, tier policy, fetch-component recipe) + wrapper + manifest

## 2. Wiring

- [ ] 2.1 Register the `Server & Tooling` category after Advanced Usage; add docs-index operator card
- [ ] 2.2 Resolve forward links from ③-5 pages (hydration↔serving-modes, ssr↔cli-reference); ③-10 will link the canonical host-mount snippet

## 3. Verification

- [ ] 3.1 E2E for new pages (title, TOC, code block presence; prod + static)
- [ ] 3.2 `ruff`/`pyright`/unit + `webcompy generate` + docs E2E + `check-doc-spec-refs.py` + `openspec validate feat-docs-server-tooling`
