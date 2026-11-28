# Design

## Context

See `proposal.md` for motivation. Currently:
- App and framework wheels under `/_webcompy-app-package/*` already embed an 8-character SHA-256 hash (`<name>-0+sha.<digest>-py3-none-any.whl`), local PyScript/Pyodide runtime assets live under `/_webcompy-assets/{PYSCRIPT_VERSION}/*`, and local WASM wheels carry package versions and Pyodide ABI tags under `/_webcompy-assets/packages/*`.
- However, `webcompy.ui._styles` (`/_webcompy-ui/index.css` and its 6 `@import url("./...")` stylesheets plus `prose.css`) and user `static_files_dir` files (`/styles/components.css`, etc.) are referenced without version hashes, and `create_asgi_app(..., mode="prod")` omitted `Cache-Control` headers on wheel and WASM routes.
- Meanwhile, `docs_app`'s `.skip-link` CSS lived in `/styles/components.css`, making initial above-the-fold skip-link hiding vulnerable to browser cache skew between `index.html` and `components.css`.

## Goals / Non-Goals

**Goals:**
- Guarantee that any change to a framework UI stylesheet or user static file produces a distinct URL query parameter (`?v=<sha256[:8]>`) in prod SSR and SSG HTML and inside `/_webcompy-ui/index.css`'s `@import` statements.
- Serve immutable browser/framework wheels and local WASM packages with `Cache-Control: public, max-age=31536000, immutable` in prod mode (and via `_headers` in `docs_app` static deployment).
- Keep all existing raw asset paths valid (`/styles/components.css`, `/_webcompy-ui/index.css` in dev mode and iframe shells, `get_styles_file()` unit APIs).
- Guarantee PyScript version upgrades remain cache-safe with `immutable` headers.

**Non-Goals:**
- Content-hashed file renaming on disk.
- Rewriting URLs in user-authored inline `<script>` / `<style>` text blocks or standalone static HTML shells like `_demos/standard.html`.
- Cache busting in `dev_mode=True`.

## Decisions

### 1. Query-Parameter Cache Busting (`?v=<sha256[:8]>`) Over Filename Hashing
- **Decision**: Compute `asset_hashes: dict[str, str]` in `resolve_build_artifacts()` when `not dev_mode` and append `?v=<hash>` at HTML render / `index.css` serve+SSG emission time.
- **Alternatives rejected**:
  - *Renaming static files or moving `/_webcompy-ui/*` into `/_webcompy-ui/<hash>/*`*: Breaks existing paths referenced by static demo shells (`_demos/standard.html`), existing tests, and relative assets (`robots.txt`, favicons, `_headers`), and would require special exclusion lists.
  - *Mutating package files in `webcompy.ui._styles`*: Violates separation between read-only package data and build-time output.
- **Child CSS Propagation**: Hashing all non-`index.css` files under `webcompy.ui._styles` first, rewriting `@import url("./<target>");` inside `index.css` to `./<target>?v=<digest>`, and then hashing the *rewritten* `index.css` guarantees that updating `tokens.css`, `code-block.css`, `prose.css`, etc. changes both the imported leaf query and `index.css`'s own `?v=` query in `<head>`.

### 2. HTML Rewriting Boundaries in `generate_html()`
- **Decision**: Add optional `asset_hashes: dict[str, str] | None = None` to `generate_html()` (defaulting to `None` for backwards compatibility with direct unit callers like `render_app_html()`). Rewrite:
  1. The auto-injected `{base_url}_webcompy-ui/index.css` link (both when emitting `<link>` and when locating it to insert `scoped_styles_html` immediately afterwards).
  2. `<link ... href="...">` tags emitted inside `head_content_html`.
  3. External `<script src="...">` dicts and `PluginScript` `src` attributes (using shallow copies so `PluginScript` instances are never mutated).
- **Normalization & Guards**: Strip `#fragment` and existing `?query`, reject external/special schemes (`//`, `://`, `data:`, `blob:`, `mailto:`, `javascript:`), skip URLs already specifying query param `v`, normalize leading `{base_url}` or `/` or `./` to a package/static-relative POSIX key, and only append `?v=<hash>` (preserving any pre-existing query params via `&v=` and trailing `#fragment`) when the normalized key exists in `asset_hashes`.

### 3. Production Cache Headers & PyScript Version-Upgrade Safety
- **Decision**:
  - In `create_asgi_app(..., mode="prod")`: emit `Cache-Control: public, max-age=31536000, immutable` on `/_webcompy-app-package/*` and `/_webcompy-assets/packages/*` (matching `/_webcompy-assets/{PYSCRIPT_VERSION}/*`), and emit `Cache-Control: public, max-age=0, must-revalidate` on `/_webcompy-ui/*` (`no-cache, must-revalidate` in `dev_mode=True`).
  - In `docs_app/static/_headers`: set `Cache-Control: public, max-age=31536000, immutable` on `/_webcompy-assets/*` and `/_webcompy-app-package/*` so Cloudflare Pages caches PyScript/Pyodide files and hashed wheels aggressively while zone TTL respects origin `max-age=0, must-revalidate` for HTML/CSS/resources.
- **PyScript Upgrade Safety Verification**:
  - `/_webcompy-assets/{PYSCRIPT_VERSION}/*` keys every PyScript, Pyodide (`pyodide.mjs`, `pyodide.asm.mjs`, `pyodide.asm.wasm`, `python_stdlib.zip`, `pyodide-lock.json`), and `micropip` file under the explicit `PYSCRIPT_VERSION` directory; HTML revalidates on every visit and immediately points `<script>`, `<link>`, `py-config.interpreter`, and `py-config.lockFileURL` to the new version directory (`_demos/standard.html` reads those parent HTML attributes dynamically).
  - `/_webcompy-assets/packages/*` holds WASM wheels whose filenames carry package versions and Pyodide ABI tags (`pyodide_<abi>_wasm32.whl`).
  - `/_webcompy-app-package/*` wheels are content-hashed (`0+sha.<digest>`) by `_content_hash_wheel()`, regardless of `WebComPyBuildConfig.version`.

### 4. Inline `.skip-link` Scoped Styles in `DocsRoot`
- **Decision**: Move `.skip-link`, `.skip-link:focus`, and `.skip-link:focus-visible` into `DocsRoot.scoped_style` (`docs_app/layout/__init__.py`) and remove them from `docs_app/static/styles/components.css`. Because scoped CSS is server-emitted inline inside `<head>` alongside the DOM, `.skip-link` stays off-screen from first paint even if an external stylesheet fails or arrives out of sync.

## Risks / Trade-offs

- [Cloudflare zone setting must use "Respect Existing Headers" on `webcompy.net`] → Documented alongside `docs_app/static/_headers`; even before Cloudflare zone TTL reaches 0, `?v=<hash>` ensures newly deployed HTML immediately requests fresh CSS URLs that bypass old CDN/browser cache entries.
- [Tests invoking `create_asgi_app(..., mode="prod")` or `generate_static_site()` see `?v=<8hex>` on `/_webcompy-ui/index.css` instead of a bare path] → Audit all existing unit/E2E tests; direct `render_app_html()` / `generate_html()` callers default to `asset_hashes=None` and stay byte-identical.
- [A static asset under `static_files_dir` is referenced with relative `./` vs `/`] → `_append_asset_version()` normalizes both forms against `base_url` cleanly.
