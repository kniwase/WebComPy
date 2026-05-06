# Design: Split Mode — Two-Wheel Split for Browser Cache Optimization

## Design Decisions

### D1: Two wheels — framework + app-with-deps
Split mode produces exactly two wheels:
- **Framework wheel**: webcompy (excl. cli/), content-hash filename
- **App wheel**: app code + all pure-Python dependencies (bundled together), content-hash filename

This is the simplest split that provides meaningful cache optimization: framework changes are rare (version upgrades only), app changes are frequent. No per-dependency wheels — dependencies are always bundled inside the app wheel.

### D2: Two local wheel URLs in `packages`
```
packages = [
    "/_webcompy-app-package/webcompy-0+sha.{hash8}-py3-none-any.whl",  # framework
    "/_webcompy-app-package/myapp-0+sha.{hash8}-py3-none-any.whl",     # app + deps
    "numpy",  # WASM from CDN
]
```
Only two local URLs, eliminating micropip transitive dependency resolution issues.

### D3: `AppConfig.wheel_mode` controls mode
```python
@dataclass
class AppConfig:
    wheel_mode: Literal["bundled", "split"] = "bundled"
```
When `wheel_mode="split"`, the build produces two wheels: framework and app-with-deps.

### D4: Cache headers differ per wheel
In dev mode:
- Framework wheel: `Cache-Control: max-age=86400, must-revalidate`
- App wheel: `Cache-Control: no-cache`

In SSG/production: ETag/Last-Modified by hosting provider.

### D5: Content-hash for both wheels
- Framework wheel: `webcompy-0+sha.{hash8}-py3-none-any.whl`
- App wheel: `{app_name}-0+sha.{hash8}-py3-none-any.whl`

Content-hash ensures automatic cache busting. Framework hash changes on WebComPy version upgrade, app hash changes on any code or dependency change.

### D6: Interaction with existing serving modes
All modes are compatible — split just adds the framework wheel URL before the app wheel URL.

## Architecture

```
BUNDLED MODE (default):
  ╔═════════════════════════════════════╗
  ║  myapp-{hash}-py3-none-any.whl     ║
  ║  ├── webcompy/ (excl. cli)         ║
  ║  ├── myapp/                        ║
  ║  ├── flask/                        ║
  ║  └── httpx/                        ║
  ╚═════════════════════════════════════╝
  packages = ["/_webcompy-app-package/myapp-{hash}-py3-none-any.whl", "numpy"]

SPLIT MODE (this change, opt-in):
  ╔══════════════════════╗  ╔═════════════════════════════════════╗
  ║ webcompy             ║  ║  myapp-{hash}-py3-none-any.whl     ║
  ║  (excl. cli)         ║  ║  ├── myapp/                        ║
  ║  -{hash}-py3-any.whl ║  ║  ├── flask/                        ║
  ╚══════════════════════╝  ║  └── httpx/                        ║
                            ╚═════════════════════════════════════╝

  packages = [
      "/_.../webcompy-0+sha.{hash8}-py3-none-any.whl",
      "/_.../myapp-0+sha.{hash8}-py3-none-any.whl",
      "numpy",
  ]
```

## Specs Affected

- `app-config` — add `wheel_mode` field
- `cli` — add `--wheel-mode` CLI flag, two-wheel serving, per-type cache headers
- `wheel-builder` — add `make_browser_webcompy_wheel()`

## Non-goals

- This does not replace the default bundled mode.
- This does not implement per-route code splitting.
- This does not split dependencies into individual wheels.
