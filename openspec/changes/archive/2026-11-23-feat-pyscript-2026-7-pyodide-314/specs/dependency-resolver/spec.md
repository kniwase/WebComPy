# Spec Delta

## MODIFIED Requirements

### Requirement: The PyScript version shall map to a Pyodide version
The PyScript version used in generated HTML (`PYSCRIPT_VERSION`) SHALL map to a specific Pyodide version for lock file resolution. Both the active pinned PyScript version and prior PyScript versions retained for version-bump sweep comparisons SHALL resolve cleanly in the mapping table.

#### Scenario: Mapping PyScript 2026.3.1
- **WHEN** the PyScript version is `2026.3.1`
- **THEN** the Pyodide version SHALL be `0.29.3`

#### Scenario: Mapping PyScript 2026.7.3
- **WHEN** the PyScript version is `2026.7.3`
- **THEN** the Pyodide version SHALL be `314.0.3`
