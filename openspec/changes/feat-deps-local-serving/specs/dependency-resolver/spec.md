# Dependency Resolver — Delta: feat-deps-local-serving

## ADDED Requirements

### Requirement: Transitive dependencies shall be fully resolved via Pyodide lock when deps_serving is local-cdn
When `deps_serving="local-cdn"`, transitive dependencies SHALL be resolved primarily via the Pyodide lock `depends` field, without requiring local installation. This eliminates the build-environment dependency limitation of `feat-dependency-bundling`.

#### Scenario: Resolving transitive dependencies without local installation
- **WHEN** `deps_serving="local-cdn"` and `httpx` is a pure-Python package in the Pyodide CDN
- **AND** `httpx` depends on `httpcore`, `h2`, and `sniffio`
- **AND** `httpcore` and `h2` are in the Pyodide lock with `depends` fields
- **THEN** all transitive dependencies SHALL be discovered by recursively walking the Pyodide lock `depends` field
- **AND** packages not in the Pyodide lock SHALL be resolved via local `importlib.metadata` as fallback

#### Scenario: Missing transitive dependency not in Pyodide lock and not installed
- **WHEN** a transitive dependency is not in the Pyodide lock and not installed locally
- **AND** `deps_serving="local-cdn"`
- **THEN** the dependency SHALL be reported as an error with instructions to add it to `AppConfig.dependencies`