# Proposal

## Why

When HTML responses revalidate immediately (`max-age=0, must-revalidate`) while unhashed CSS or static files remain cached by a browser or CDN (for example under Cloudflare's default 4-hour browser cache TTL), a deployment can pair fresh HTML markup with a stale stylesheet — such as exposing `Skip to main content` unstyled at the top of `https://webcompy.net/` after PR `#317` merged. Meanwhile, truly content-addressed or version-prefixed artifacts (`/_webcompy-app-package/*` wheels and `/_webcompy-assets/packages/*` WASM wheels in `webcompy-cli` prod mode, and static deploys on Cloudflare Pages) lacked explicit `immutable` caching headers.

## What Changes

- **Static & Framework UI CSS Cache Busting (`cli`, `css-architecture`)**:
  - Compute deterministic 8-character SHA-256 content hashes in `resolve_build_artifacts()` when `dev_mode=False` for all `webcompy.ui._styles` files (hashing leaf stylesheets first, rewriting `@import url("./<file>");` inside `index.css` to `./<file>?v=<hash>`, then hashing the rewritten `index.css`) and all files under `static_files_dir`.
  - Append `?v=<hash>` in `generate_html()` (prod SSR and SSG) to the auto-injected `/_webcompy-ui/index.css` stylesheet link as well as matching same-origin `<link href>` tags in `<head>` and external `<script src>` tags, preserving existing query parameters and fragments while leaving `dev_mode=True` unversioned.
  - Serve the rewritten `index.css` from `/_webcompy-ui/index.css` in prod server mode and write it into `dist/_webcompy-ui/index.css` during `generate_static_site()`, setting `public, max-age=0, must-revalidate` in prod (`no-cache, must-revalidate` in dev) on `/_webcompy-ui/*`.
- **Immutable Cache Headers for Versioned/Hashed Bundles (`cli`)**:
  - Emit `Cache-Control: public, max-age=31536000, immutable` on `/_webcompy-app-package/*` and `/_webcompy-assets/packages/*` in `create_asgi_app(..., mode="prod")` (keeping dev-mode headers unchanged).
- **`docs_app` Resilience & Static Host Headers (`docs-site-documents`)**:
  - Move `.skip-link` / `:focus` / `:focus-visible` styling from `docs_app/static/styles/components.css` into `DocsRoot.scoped_style` so it is inlined into HTML `<head>` and resilient to external stylesheet cache skew or failure.
  - Add `docs_app/static/_headers` so static hosting (Cloudflare Pages) serves `/_webcompy-assets/*` and `/_webcompy-app-package/*` with `Cache-Control: public, max-age=31536000, immutable` even when zone-level cache TTL respects origin `max-age=0` headers for HTML/unhashed files.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `cli`: Compute static/UI content hashes on prod/SSG builds, rewrite `index.css` `@import`s and HTML `<link>`/`<script>` asset references with `?v=<hash>`, and serve `/_webcompy-app-package/*` and `/_webcompy-assets/packages/*` with `immutable` cache headers in prod mode.
- `css-architecture`: Allow the auto-injected `/_webcompy-ui/index.css` stylesheet link in SSR/SSG `<head>` output to include a `?v=<hash>` query parameter while preserving layer-order placement before all component scoped styles.
- `docs-site-documents`: Inline `.skip-link` styles inside `DocsRoot.scoped_style` and ship `docs_app/static/_headers` for immutable runtime and wheel caching.

## Known Issues Addressed

- **Post-deploy HTML/CSS cache skew on static hosts and CDN edges**: Prevents fresh SSR/SSG HTML from loading stale unversioned framework UI CSS or user static assets, while also ensuring `.skip-link` remains off-screen even if external CSS is delayed.
- **Unnecessary revalidation of immutable wheels/runtime assets**: Adds `immutable` `Cache-Control` headers for content-hashed wheels and versioned WASM/PyScript packages in prod server and `docs_app` static hosting.
- **Remaining tracked constraints**: Multi-app `ThemeManager` isolation and PyPI release availability in project Known Issues remain unchanged.

## Non-goals

- Renaming user static files to content-hashed filenames on disk (`dist/styles/components.<hash>.css`), which would break direct references to files under `static/`.
- Generating hosting-specific header files (such as `_headers` or Nginx configs) automatically inside `webcompy generate`.
- Mutating raw package resource bytes returned by `webcompy.ui._styles.get_styles_file()` / `get_styles_files()`.
- Applying cache-busting query strings in `dev_mode=True` (hot reload relies on live re-reading without stale hashes).

## Impact

- **Server (`packages/webcompy-server`)**: `webcompy_server/_html.py` (`generate_html` gains optional `asset_hashes` parameter and URL rewriting helpers).
- **CLI (`packages/webcompy-cli`)**: `webcompy_cli/_build.py` (`BuildArtifacts`, `_compute_asset_hashes`), `webcompy_cli/_server.py` (cache headers, rewritten `index.css`, passing `asset_hashes`), `webcompy_cli/_generate.py` (emitting rewritten `index.css`).
- **Docs app (`docs_app`)**: `layout/__init__.py` (`DocsRoot.scoped_style`), `static/styles/components.css`, `static/_headers` (new), `documents/server_serving_modes.md`, `documents/api_server_cli.md`.
- **Tests & Specs**: Unit tests for asset hashing, `@import` rewriting, HTML `<link>`/`<script>` rewriting, ASGI cache headers, SSG output, `DocsRoot` scoped styles, and Playwright E2E skip-link focus positioning.
