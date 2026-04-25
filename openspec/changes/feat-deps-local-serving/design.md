# Design: Deps Local Serving — Same-Origin Pure-Python Package Serving

## Design Decisions

### D1: Pure-Python packages are downloaded from Pyodide CDN at build time
When `deps_serving="local-cdn"`, pure-Python packages referenced in the lock file are downloaded from the Pyodide CDN as wheel files and either extracted into the app bundle (bundled mode) or served as separate wheel files (split mode, requires `feat-split-mode`).

### D2: Transitive dependencies are resolved via Pyodide lock `depends` field
The Pyodide lock's `depends` field lists immediate dependencies for each package. These are walked recursively to discover the full dependency tree. For dependencies not in the Pyodide lock, local `importlib.metadata` is used as fallback.

### D3: Build environment independence
This change eliminates the requirement for pure-Python packages to be installed locally. The Pyodide CDN provides both the wheel files and the dependency metadata, enabling complete resolution without local installation.

### D4: `AppConfig.deps_serving` controls the serving mode
```python
@dataclass
class AppConfig:
    deps_serving: Literal["bundled", "local-cdn"] = "bundled"
```
When `deps_serving="bundled"` (default), behavior is identical to `feat-dependency-bundling`. When `deps_serving="local-cdn"`, pure-Python packages are downloaded from the Pyodide CDN and bundled into the app wheel.

### D5: Lock file gains `downloaded_packages` section
The lock file records downloaded packages with their URLs and SHA256 hashes for reproducibility and verification.

### D6: Two delivery modes for downloaded packages
Downloaded pure-Python packages can be delivered in two ways:
- **Bundled (default)**: Extracted and included in the single app wheel. No change to `packages` in HTML.
- **Separate wheels (requires `feat-split-mode`)**: Served as individual wheel files.

This change initially implements bundled mode only.

## Architecture

```
DEFAULT (feat-dependency-bundling):
  Pure-Py ──────── Bundled (local install required)
  Transitive deps ──── importlib.metadata + Pyodide lock depends (auxiliary)
  Limitation: Transitive deps not installed locally cannot be resolved

LOCAL-CDN (feat-deps-local-serving):
  Pure-Py ──────── Downloaded from Pyodide CDN → Extracted into bundle
  Transitive deps ──── Pyodide lock depends (primary) + importlib.metadata (fallback)
  Benefit: Build-environment independent, complete transitive resolution
```

## Specs Affected

- `app-config` — add `deps_serving` field
- `cli` — download logic, wheel extraction
- `lockfile` — add `downloaded_packages` section
- `dependency-resolver` — add Pyodide lock-based transitive resolution