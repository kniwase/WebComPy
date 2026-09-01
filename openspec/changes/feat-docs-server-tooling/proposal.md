# Proposal: feat-docs-server-tooling

## Why

The server/CLI surface (dev server modes, SSG, project config split, ASGI embed/mount, serving modes, testing utilities) is the reason teams pick WebComPy for production apps, yet none of it is documented outside spec files. Advanced-usage pages (SSR/SSG, hydration) already refer forward to "Server & Tooling" content this change supplies.

## What Changes

- Create the `Server & Tooling` category (its own top-level category section after Advanced Usage, pages under `/documents/server/`) with five pages:
  - `cli-reference` — every `python -m webcompy` subcommand (`start`, `generate`, `init`, `lock`, `inspect`) with flags, exit behavior, and examples; the `inspect` browser-verification workflow
  - `project-configuration` — the two-file config model (`pyproject.toml` browser deps vs `webcompy_config.py` build/server), `WebComPyBuildConfig`/`WebComPyServerConfig` field guide, resource allow-list, lockfile workflow
  - `asgi-integration` — `create_asgi_app`, mounting WebComPy inside FastAPI/Starlette hosts (`configure_server_context`, `root_app`, `base_url` pairing, blocked paths, mount validation), and mounting other ASGI apps under WebComPy (`WebComPyServerConfig.mounts`)
  - `serving-modes` — CDN vs local wasm/runtime, standalone, wheel modes (bundled/split), dependency resolution classes, offline/self-hosted deployments
  - `testing` — `webcompy_testing` tour: `TestRenderer`, fake ports, ASGI test helpers, scope helpers; unit/browser/E2E tier policy of an app project
- Add an "Operators' cheat sheet" card on the docs index once Server & Tooling pages exist.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `docs-site-documents`: `Server & Tooling` category (URL prefix `/documents/server/`, page set) added to the category model.

## Impact

- 5 new `.md` + wrappers + manifest category; docs index card addition; E2E page tests; back-links from ③-5 pages (hydration↔serving, ssr↔cli)
- No package changes

## Known Issues Addressed

None.

## Non-goals

- CI/CD platform recipes (outside framework scope)
- Deployment of the docs site itself
