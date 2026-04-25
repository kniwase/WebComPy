# Lock File — Delta: feat-deps-local-serving

## ADDED Requirements

### Requirement: The lock file shall record downloaded packages for reproducibility
When `deps_serving="local-cdn"`, `webcompy-lock.json` SHALL include a `downloaded_packages` section recording the download URLs and SHA256 hashes of pure-Python packages downloaded from the Pyodide CDN.

#### Scenario: Lock file with downloaded packages
- **WHEN** a lock file is generated with `deps_serving="local-cdn"`
- **THEN** the `downloaded_packages` section SHALL contain entries for each downloaded package with `url`, `sha256`, and `source` (`"explicit"` or `"transitive"`)

#### Scenario: Lock file without downloaded packages
- **WHEN** a lock file is generated with `deps_serving="bundled"` (default)
- **THEN** the `downloaded_packages` section SHALL be omitted or empty