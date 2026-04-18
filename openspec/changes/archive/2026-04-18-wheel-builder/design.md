## Context

WebComPy's CLI builds Python wheels for browser deployment using `setuptools.setup()` called programmatically via `sys.argv` manipulation. This triggers `SetuptoolsDeprecationWarning` because direct `setup.py` invocation is deprecated. The current approach outputs two separate wheels — one for the framework and one for the user application — which means two HTTP requests and two package installations in the browser.

Additionally:
- Non-Python resources (JSON, CSS, images) can only be served via the `static/` directory as HTTP files — there is no mechanism to include them inside the wheel for `importlib.resources` access
- `typing_extensions` is listed as a runtime dependency but only used for `ParamSpec`, which is available in `typing` since Python 3.10+ (WebComPy requires 3.12+)
- `setuptools` and `wheel` are dev dependencies solely for this wheel building code

The wheel format (PEP 427) is straightforward: a ZIP file with `.whl` extension containing the package source tree and a `.dist-info` directory with `METADATA`, `WHEEL`, `top_level.txt`, and `RECORD` files. Since we only need basic pure-Python wheels (no C extensions, no entry points, no complex metadata), a manual builder is feasible.

## Goals / Non-Goals

**Goals:**
- Eliminate `setuptools` and `wheel` dependencies from the project
- Produce PEP 427-compliant wheels using only Python standard library (`zipfile`, `hashlib`, `pathlib`)
- Bundle webcompy framework + user application into a single wheel by default
- Support `package_data` for including non-Python files in the wheel
- Remove `typing_extensions` runtime dependency
- Maintain backward compatibility of browser-side behavior (PyScript can still load and import packages)

**Non-Goals:**
- Building wheels for general Python packaging (we only build pure-Python `py3-none-any` wheels)
- Supporting `data_files` (files installed outside the package directory)
- Changing PyScript's package loading mechanism
- Supporting entry points, console scripts, or other setuptools features
- Replacing hatchling as the build backend for the webcompy package itself

## Decisions

### Decision 1: Manual ZIP-based wheel builder vs. subprocess invocation

**Choice: Manual ZIP-based builder**

Alternatives considered:
- `python -m build` subprocess: Adds latency, requires build isolation, hard to customize for runtime wheel generation, still needs setuptools/wheel as build backend
- `pip wheel` subprocess: Even heavier, not suitable for runtime use
- Custom build backend: Over-engineered for this use case

Rationale: PEP 427 wheels are ZIP files with a well-defined structure. We need basic pure-Python wheels with minimal metadata (`Name`, `Version`, `Wheel-Version`, `Root-Is-Purelib`, `Tag`). A manual builder using `zipfile` and `hashlib` is ~100 lines, has zero external dependencies, and gives us full control over bundling and `package_data`.

### Decision 2: Bundled wheel by default

**Choice: Bundle framework + app into single wheel, remove two-wheel path**

The bundled approach:
```
webcompy-app-{version}-py3-none-any.whl
├── webcompy/              ← framework
├── app/                   ← user application
└── webcompy_app-{version}.dist-info/
```

Alternatives considered:
- Keep two-wheel as default, add bundle as option: More code paths to maintain, defaults matter
- Bundle everything including `typing_extensions`: Overly aggressive, external deps should stay external

Rationale: WebComPy is pre-1.0, so breaking changes are acceptable. A single wheel reduces HTTP requests in the browser (from 2 wheel downloads to 1), eliminates version mismatch between framework and app, and simplifies the HTML configuration. The `typing_extensions` removal further reduces the package list.

### Decision 3: Package data format

**Choice: setuptools-compatible glob patterns**

```python
WebComPyConfig(
    app_package=Path("myapp"),
    package_data={
        "myapp": ["data/*.json", "templates/*.html"],
    },
)
```

This mirrors the `setuptools` `package_data` format developers already know. Glob patterns are resolved relative to each package directory. Files matching the patterns are included in the wheel inside the package tree, making them accessible via `importlib.resources`.

Alternatives considered:
- Directory-only specification (`{"myapp": ["data/"]}`): Less precise, would include unwanted files
- Explicit file list: Too verbose, requires manual updates when adding files
- Custom format: Unnecessary when setuptools convention exists

### Decision 4: Wheel file name and package naming

**Choice: Use the app package name for the bundled wheel**

The bundled wheel uses `webcompy-app` as the distribution name (normalized from the app package directory name). The `top_level.txt` lists both `webcompy` and the app package name. This ensures:
- `import webcompy` works (framework code is in the wheel)
- `import myapp` works (app code is in the wheel)
- PyScript installs the wheel and both top-level packages become importable

### Decision 5: typing_extensions removal approach

**Choice: Replace `from typing_extensions import ParamSpec` with `from typing import ParamSpec` in all three files, remove from dependencies and HTML package list**

Python 3.12 includes `ParamSpec` in `typing` (it was added in 3.10). Since WebComPy requires Python >=3.12, this is safe.

## Risks / Trade-offs

- **[PyScript compatibility with multi-top-level wheel]** → PyScript uses `micropip` which supports multi-top-level packages. Verify with e2e tests that `import webcompy` and `import app` both work from a single wheel. Mitigation: The e2e test suite runs in a real browser and will catch import failures.

- **[Breaking change for existing projects]** → The HTML payload changes from two wheel references to one, and `typing_extensions` is removed from the package list. Existing `WebComPyConfig` objects still work without modification (no new required fields). Mitigation: WebComPy is pre-1.0 with no stability guarantee.

- **[Package discovery edge cases]** → The manual `find_packages` replacement needs to handle the same cases: namespace packages with `__init__.py`, nested packages, and `__pycache__` exclusion. Mitigation: The only consumers are `webcompy` (known structure) and user apps (typically simple flat packages). Test with both.

- **[importlib.resources compatibility in Pyodide]** → Pyodide supports `importlib.resources` (and the older `pkg_resources`). Package data included in wheels should be accessible. Mitigation: Test with e2e suite.

- **[Glob pattern portability]** → `pathlib.glob` behavior differs across platforms. Since WebComPy runs on a server (Linux/macOS typically), and we use `Path.glob()`, this should be fine. Mitigation: Normalize separators in archiving.

## Open Questions

- Should the bundled wheel name be configurable via `WebComPyConfig`, or always derived from the app package name? (Current proposal: always derived, e.g., `app` → `app-{version}-py3-none-any.whl`)
- Should we provide a migration guide for users who were manually referencing the old two-wheel URLs in custom configurations?