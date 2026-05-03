## MODIFIED Requirements

### Requirement: The lockfile shall record all runtime assets

When `runtime_serving="local"`, the lockfile SHALL record all runtime asset files in the `runtime_assets` field. This SHALL include all `.js` and `.css` files from the PyScript core bundle (not just `core.js` and `core.css`) and all Pyodide runtime files.

Each entry in `runtime_assets` SHALL have the filename as key and an object with `url` and `sha256` fields.

Lockfile population SHALL be progressive: `generate_lockfile()` initially records `core.js`/`core.css` with placeholder entries (no SHA256). After `download_runtime_assets()` completes, `verify_and_update_runtime_assets()` SHALL replace the `runtime_assets` dict with the complete set of downloaded files, each with verified SHA256.

#### Scenario: Initial lockfile generation with runtime_serving=local

- **WHEN** `webcompy lock` is run with `runtime_serving="local"` (or `standalone=True`)
- **THEN** the lockfile SHALL contain `runtime_assets` with `core.js` and `core.css` entries
- **AND** each entry SHALL have a `url` field pointing to the PyScript release URL
- **AND** SHA256 fields SHALL be `null` until files are actually downloaded

#### Scenario: Lockfile updated after generate/start downloads bundle

- **WHEN** `webcompy generate` or `webcompy start` runs with `runtime_serving="local"`
- **AND** the PyScript offline bundle is downloaded and extracted
- **THEN** `runtime_assets` in the lockfile SHALL be replaced with entries for ALL downloaded `.js` and `.css` files from the bundle
- **AND** each entry SHALL have the filename as key (e.g., `core-BuLtL7jM.js`)
- **AND** each entry SHALL have a `sha256` field with the computed hash

#### Scenario: Lockfile regeneration when stale bundle files

- **WHEN** an existing lockfile has `runtime_assets` containing only `core.js` and `core.css`
- **AND** `webcompy generate` or `webcompy start` is run with `runtime_serving="local"`
- **THEN** `verify_and_update_runtime_assets()` SHALL replace the `runtime_assets` dict with the complete set of downloaded files
- **AND** SHA256 hashes SHALL be computed and recorded for all files