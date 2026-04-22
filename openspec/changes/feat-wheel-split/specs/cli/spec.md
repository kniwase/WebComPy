# CLI — Delta: feat-wheel-split

## Changes

### Updated: Two-wheel architecture replaces single bundled wheel

The dev server and SSG SHALL produce two separate wheels:
1. A browser-only webcompy framework wheel excluding `webcompy/cli/`
2. An app wheel containing app code and bundled pure-Python dependencies

The generated HTML PyScript config SHALL reference both wheel URLs plus C-extension/Pyodide built-in package names (not pure-Python dependencies).

### Added: Cache-Control headers for wheel files

- Framework wheel: `Cache-Control: max-age=86400, must-revalidate`
- App wheel in dev mode: `Cache-Control: no-cache`

### Added: Stable wheel URLs

Wheel URLs SHALL NOT include version suffixes. Framework: `/_webcompy-app-package/webcompy-py3-none-any.whl`. App: `/_webcompy-app-package/{app_name}-py3-none-any.whl`.

### Added: Dependency bundling into app wheel

Pure-Python dependencies listed in `AppConfig.dependencies` SHALL be bundled into the app wheel. Only C-extension / Pyodide built-in packages SHALL remain in `py-config.packages`.