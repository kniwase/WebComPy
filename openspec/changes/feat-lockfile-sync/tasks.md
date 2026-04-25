# Tasks: Lock File Sync — Bidirectional Version Synchronization

- [ ] **Task 1: Implement requirements.txt export from lock file**

**Estimated time: ~1 hour**

### Steps

1. Create `webcompy/cli/_lockfile_sync.py`.
2. Implement `export_requirements(lockfile: Lockfile, path: pathlib.Path) -> None`:
   - Iterate `lockfile.bundled_packages` → write `{name}=={version}` lines.
   - Iterate `lockfile.pyodide_packages`, skip entries with `is_wasm=True` → write `{name}=={version}` for non-WASM entries.
   - Sort entries alphabetically for deterministic output.
   - Write to `path` with a header comment indicating generation by webcompy.
   - Create parent directories if needed.
3. Write unit tests.

### Acceptance Criteria

- Exported `requirements.txt` contains pinned versions for all bundled and non-WASM Pyodide packages.
- WASM packages are excluded.
- Entries are sorted alphabetically.
- Custom output path works.

---

- [ ] **Task 2: Implement requirements.txt sync comparison**

**Estimated time: ~1 hour**

### Steps

1. Implement `sync_from_requirements_txt(lockfile: Lockfile, path: pathlib.Path) -> list[str]` in `_lockfile_sync.py`:
   - Parse `requirements.txt` lines matching `{name}=={version}` pattern.
   - Skip comment lines and non-`==` specifiers.
   - For each parsed entry, compare with the lock file.
   - Return a list of report lines (matching, mismatch, informational).
2. Write unit tests with various `requirements.txt` content patterns.

### Acceptance Criteria

- Matching versions are reported as `✓`.
- Mismatched versions are reported with both versions and a suggested install command.
- Extra entries (not in lock file) are reported as informational.
- WASM packages in `requirements.txt` are reported as not applicable.
- Non-`==` specifiers are skipped with a note.

---

- [ ] **Task 3: Implement pyproject.toml sync comparison**

**Estimated time: ~1.5 hours**

### Steps

1. Implement `sync_from_pyproject_toml(lockfile: Lockfile, path: pathlib.Path) -> list[str]` in `_lockfile_sync.py`:
   - Parse `pyproject.toml` using `tomllib` (Python 3.11+).
   - Read `[project.dependencies]` list.
   - Parse PEP 508 dependency specifiers (e.g., `markupsafe>=2.0`, `requests==2.32.4`).
   - For `==` pinned entries, compare with lock file versions.
   - For non-pinned entries (ranges), report as informational and suggest pinning.
   - Return a list of report lines.
2. Write unit tests.

### Acceptance Criteria

- `==` pinned entries are compared with lock file.
- Non-pinned entries are reported with a suggestion to pin.
- Missing `[project.dependencies]` section is handled gracefully.
- Invalid `pyproject.toml` is reported as an error.

---

- [ ] **Task 4: Implement `webcompy lock --install` convenience command**

**Estimated time: ~0.5 hours**

### Steps

1. Implement `install_requirements(lockfile: Lockfile, path: pathlib.Path | None = None) -> None` in `_lockfile_sync.py`:
   - Generate `requirements.txt` using `export_requirements()`.
   - Run `pip install -r {path}` via `subprocess.run`.
   - Propagate pip's exit code.
   - Print pip's stdout/stderr.
2. Write unit tests with mocked `subprocess.run`.

### Acceptance Criteria

- `install_requirements()` generates a requirements file, then runs `pip install -r`.
- pip's exit code is propagated.
- pip's output is printed to the user.

---

- [ ] **Task 5: Extend `webcompy lock` CLI with new flags**

**Estimated time: ~1 hour**

### Steps

1. Modify `webcompy/cli/_argparser.py`:
   - Add `--export-requirements` flag to the `lock` subcommand.
   - Add `--sync-from` flag (argument: source file path) to the `lock` subcommand.
   - Add `--install` flag to the `lock` subcommand.
   - Add `--path` flag (argument: output file path) for use with `--export-requirements` and `--install`.
   - Ensure flags are mutually exclusive.
2. Modify `webcompy/cli/_lock.py`:
   - Add dispatch logic for the new operations.
   - Load existing lock file for export/sync/install operations (error if missing).
3. Write unit tests for argument parsing.

### Acceptance Criteria

- `webcompy lock --export-requirements` runs the export operation.
- `webcompy lock --export-requirements --path custom.txt` uses the custom path.
- `webcompy lock --sync-from requirements.txt` runs the comparison.
- `webcompy lock --sync-from pyproject.toml` runs the pyproject.toml comparison.
- `webcompy lock --install` runs the install operation.
- `webcompy lock --export-requirements --install` reports a mutual exclusion error.
- Default `webcompy lock` (no flags) still generates/updates the lock file.

---

- [ ] **Task 6: Update unit and E2E tests**

**Estimated time: ~1 hour**

### Steps

1. Add tests for `_lockfile_sync.py`:
   - Export with various lock file contents.
   - Sync with matching/mismatching `requirements.txt`.
   - Sync with `pyproject.toml` (pinned and unpinned entries).
   - Install with mocked subprocess.
2. Verify existing tests still pass.
3. Run full test suite.

### Acceptance Criteria

- All existing tests pass.
- New tests for export/sync/install pass.
- `webcompy lock --export-requirements` produces correct `requirements.txt`.
- `webcompy lock --sync-from` reports correct comparisons.