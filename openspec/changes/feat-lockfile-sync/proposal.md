# Proposal: Lock File Sync — Bidirectional Version Synchronization with External Package Managers

## Summary

Add bidirectional version synchronization between `webcompy-lock.json` and external package management tools (`requirements.txt`, `pyproject.toml`). The lock file records dependency versions, but currently no mechanism exists to either export those versions to a format consumable by `pip`/`uv`/`poetry`, or to import versions from an existing Python environment configuration. This change introduces `webcompy lock --export-requirements` to generate installable dependency files from the lock file, and `webcompy lock --sync-from` to import version constraints from existing configuration files, ensuring SSR and browser runtime consistency.

## Motivation

1. **SSR/Browser version consistency**: The SSR/SSG server runs Python components locally using the installed package versions, while the browser uses versions bundled from the same local environment. If the lock file records `markupsafe==2.1.5` but the local environment has `3.0.2`, the SSR output may differ from what the browser expects during hydration. The Phase 0 validation catches this mismatch, but the developer needs a convenient way to fix it.

2. **CI reproducibility**: A CI pipeline running `webcompy generate` needs the exact dependency versions listed in the lock file. Currently, there is no way to generate an installable requirements file from the lock file.

3. **Team consistency**: When a developer commits `webcompy-lock.json`, other team members need to install matching versions. An export mechanism converts lock file versions to `pip install -r requirements.txt`.

4. **Existing project onboarding**: Projects that already use `pyproject.toml` or `requirements.txt` should be able to synchronize those versions into the lock file, avoiding manual duplication.

## Known Issues Addressed

- Addresses the version mismatch scenario identified during `feat-dependency-bundling` implementation, where `get_bundled_deps()` silently uses whatever local version is installed regardless of what the lock file records.

## Non-goals

- Automatic package downloading from PyPI (no wheel fetching)
- Resolving version conflicts between the lock file and external config (only strict equality)
- Supporting `Pipfile`/`Pipfile.lock` or other non-standard formats
- Changing the lock file schema (the schema remains unchanged from `feat-dependency-bundling`)
- Removing the dependency on local package installation (SSR requires local packages)

## Dependencies

- **Requires** `feat-dependency-bundling` (lock file validation from Phase 0)
- **Informed by** `feat-dependency-bundling` (lock file schema and dependency classification)

## Design

### Part 1: Export — Lock file to installable formats

`webcompy lock --export-requirements` generates a `requirements.txt` file containing version-pinned entries for all packages that require local installation (bundled packages + non-WASM Pyodide CDN packages). WASM-only packages are excluded since they are not needed locally.

### Part 2: Import — External config to lock file version hints

`webcompy lock --sync-from <source>` reads version constraints from external configuration files and reconciles them with the lock file. Supported sources:
- `requirements.txt`: Parse `package==version` lines
- `pyproject.toml`: Read `[project.dependencies]` (PEP 621)

The sync operation compares detected versions with lock file entries and reports mismatches. It does NOT automatically modify the lock file — instead, it suggests running `webcompy lock` to regenerate after installing the correct versions.

### Part 3: Convenience — Combined workflow

`webcompy lock --install` is a shorthand that runs `--export-requirements` followed by `pip install -r requirements.txt`, installing the exact versions recorded in the lock file.

## Specs Affected

- `lockfile` — adds export/import/sync requirements
- `cli` — adds CLI flags for `webcompy lock` command
