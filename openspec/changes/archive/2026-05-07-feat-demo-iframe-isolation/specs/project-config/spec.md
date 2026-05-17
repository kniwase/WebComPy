## MODIFIED Requirements

### Requirement: AppConfig dependencies shall default to None and support auto-population from pyproject.toml
`AppConfig.dependencies` SHALL default to `None`. When `None`, the CLI SHALL auto-populate it from `pyproject.toml` using the group specified by `AppConfig.dependencies_from`. When set to an explicit list (including an empty list `[]`), it SHALL be used as-is. Version specifiers in `pyproject.toml` entries SHALL be stripped — only package names are used. An empty list SHALL be valid and SHALL indicate that no browser dependencies are required.

#### Scenario: Configuring dependencies with dependencies_from
- **WHEN** a developer creates `AppConfig(dependencies=None, dependencies_from="browser")`
- **AND** `pyproject.toml` has `[project.optional-dependencies] browser = ["numpy", "matplotlib"]`
- **THEN** the CLI SHALL resolve `dependencies` to `["numpy", "matplotlib"]` before lock file generation

#### Scenario: Configuring dependencies explicitly (backward compatible)
- **WHEN** a developer creates `AppConfig(dependencies=["numpy", "matplotlib"])`
- **THEN** the CLI SHALL use the explicit list without reading `pyproject.toml`

#### Scenario: Configuring empty dependencies explicitly
- **WHEN** a developer creates `AppConfig(dependencies=[])`
- **THEN** the CLI SHALL use the empty list without reading `pyproject.toml`
- **AND** the lock file SHALL be generated with no browser dependencies
- **AND** `py-config.packages` SHALL contain only the app wheel

#### Scenario: Default dependencies_from reads project.dependencies
- **WHEN** a developer creates `AppConfig(dependencies=None)` without `dependencies_from`
- **THEN** the CLI SHALL read `[project.dependencies]` from `pyproject.toml`

#### Scenario: dependencies_from and sync_group mismatch
- **WHEN** `AppConfig(dependencies_from="browser")` and `LockfileSyncConfig(sync_group="deps")` differ
- **THEN** a warning SHALL be emitted indicating potential inconsistency
