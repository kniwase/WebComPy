# Design: Lock File Sync — Bidirectional Version Synchronization

## Design Decisions

### D1: Export generates `requirements.txt` with pinned versions

The simplest and most universal format for pinned dependencies is `requirements.txt` with `package==version` lines. This format is consumable by `pip install -r`, `uv pip install -r`, and many CI systems.

Only packages that require local installation are included:
- `bundled_packages` (all entries)
- `pyodide_packages` with `is_wasm=False` (non-WASM Pyodide CDN packages that are bundled locally)

WASM-only `pyodide_packages` are excluded because they are not needed in the local environment — they are loaded from the Pyodide CDN at browser runtime and are typically C extensions compiled for WASM.

### D2: Import reads `requirements.txt` and `pyproject.toml` only

Two import sources are supported:

1. **`requirements.txt`**: Parse lines matching `package==version` or `package>=version` patterns. Only `==` pinned versions are used for locking; other specifiers are reported as warnings.

2. **`pyproject.toml`**: Read `[project.dependencies]` (PEP 621 format). Entries like `markupsafe>=2.0` or `markupsafe==2.1.5` are parsed. Only `==` pinned versions contribute to lock file sync; version ranges are reported as informational.

Other formats (`Pipfile`, `poetry.lock`, `uv.lock`) are out of scope. `poetry.lock` and `uv.lock` are lock files in their own right — synchronizing between them and `webcompy-lock.json` introduces complex version resolution that is better handled by running `webcompy lock` after `poetry install` or `uv sync`.

### D3: Sync is compare-and-report, not auto-modify

`--sync-from` compares the detected versions with the lock file entries and:
- Reports matching versions (informational)
- Reports mismatches (warnings with suggested fixes)
- Reports packages in external config but not in lock file (informational — may be non-browser dependencies)
- Reports packages in lock file but not in external config (informational — transitive deps)

It does NOT modify the lock file. The correct workflow is:
1. Run `webcompy lock --sync-from requirements.txt` to see what differs
2. Install or update packages as needed
3. Run `webcompy lock` to regenerate the lock file

This avoids the complexity of partial lock file updates and keeps the lock file as the single source of truth for WebComPy builds.

### D4: `--install` is a convenience shorthand

`webcompy lock --install` combines export + pip install:
1. Generate `requirements.txt` to a temporary file
2. Run `pip install -r {tempfile}` using `subprocess`
3. Report results

This avoids requiring the developer to manually run `--export-requirements` then `pip install`. The command uses `pip` (always available since the user runs Python), and falls back to `uv pip` if `pip` is not found (edge case in uv-managed environments).

### D5: Exported file path is configurable

Both `--export-requirements` and `--install` accept an optional path for the generated `requirements.txt`. Default is `requirements.txt` in the current working directory (same level as `webcompy_config.py`).

## Architecture

### Command Flow

```
webcompy lock
├── (no flags)              → generate/update lock file (existing behavior)
├── --export-requirements   → generate requirements.txt from lock file
│   [--path FILE]             default: ./requirements.txt
├── --sync-from SOURCE      → compare external config with lock file
│                              SOURCE: requirements.txt | pyproject.toml
├── --install               → export + pip install
│   [--path FILE]             default: ./requirements.txt
└── (sub-commands are mutually exclusive)
```

### Export Logic

```
webcompy-lock.json
    │
    ├── bundled_packages:
    │     markupsafe → version="2.1.5"  ──→  markupsafe==2.1.5
    │     click → version="8.1.7"       ──→  click==8.1.7
    │
    ├── pyodide_packages:
    │     numpy → is_wasm=True           ──→  (excluded)
    │     jinja2 → is_wasm=False         ──→  jinja2==3.1.6
    │
    └── result: requirements.txt
         markupsafe==2.1.5
         click==8.1.7
         jinja2==3.1.6
```

### Import Logic

```
requirements.txt
    charset-normalizer==3.4.0
    requests==2.32.4
    numpy==2.2.5           ← won't match (WASM, excluded from local)
    some-tool==1.0.0       ← not in lock file (informational)
    │
    ├── Compare with lock file versions
    │
    └── Report:
         ✓ charset-normalizer: 3.4.0 (matches)
         ⚠ requests: lock=2.32.4, requirements.txt=2.31.0 (mismatch)
         ℹ numpy: WASM package, not applicable for local install
         ℹ some-tool: not in lock file (non-browser dependency?)
```

### Import from pyproject.toml

```
[project]
dependencies = [
    "markupsafe==2.1.5",
    "requests>=2.31",
]
    │
    ├── Compare with lock file versions
    │
    └── Report:
         ✓ markupsafe: 2.1.5 (matches)
         ⚠ requests: pinned version required for sync, got ">=2.31"
                    lock file has 2.32.4
                    Suggest: pip install requests==2.32.4
```

## Implementation

### `_lock.py` Extensions

```python
def lock_command() -> None:
    # Existing: no flags → generate/update lock file
    # New:
    # --export-requirements [--path FILE] → export_requirements()
    # --sync-from SOURCE → sync_from()
    # --install [--path FILE] → install_requirements()
```

### `_lockfile_sync.py` (New Module)

```python
def export_requirements(
    lockfile: Lockfile,
    path: pathlib.Path,
) -> None: ...

def sync_from_requirements_txt(
    lockfile: Lockfile,
    path: pathlib.Path,
) -> list[str]: ...  # returns report lines

def sync_from_pyproject_toml(
    lockfile: Lockfile,
    path: pathlib.Path,
) -> list[str]: ...  # returns report lines

def install_requirements(
    lockfile: Lockfile,
    path: pathlib.Path | None = None,
) -> None: ...
```

## Specs to Update

- `openspec/specs/lockfile/spec.md` — add export/import/sync requirements
- `openspec/specs/cli/spec.md` — add CLI flags for `webcompy lock`

## Non-goals (restated)

- Automatic package downloading from PyPI
- Synchronizing with `poetry.lock` or `uv.lock`
- Modifying `requirements.txt` or `pyproject.toml` in place
- Removing dependency on local package installation