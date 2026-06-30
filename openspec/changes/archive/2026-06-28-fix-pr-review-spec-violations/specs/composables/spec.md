## ADDED Requirements

### Requirement: use_theme shall be importable from the public `webcompy.ui.theme` and `webcompy.ui.composables` paths

`use_theme` SHALL be importable from both `webcompy.ui.theme` and `webcompy.ui.composables`. Both import paths SHALL refer to the same function object. The function body SHALL declare its framework dependencies (the active `ThemeManager` and friends) via lazy imports inside the function body to avoid the circular import that arises from the public re-export chain.

The previously private `webcompy.ui._composables` module path SHALL NOT be part of the public API; user code that imports from it will fail because the module is removed.

#### Scenario: Importing use_theme from webcompy.ui.theme
- **WHEN** a developer writes `from webcompy.ui.theme import use_theme`
- **THEN** the import SHALL succeed
- **AND** the imported `use_theme` SHALL be callable

#### Scenario: Importing use_theme from webcompy.ui.composables
- **WHEN** a developer writes `from webcompy.ui.composables import use_theme`
- **THEN** the import SHALL succeed
- **AND** the imported `use_theme` SHALL be callable

#### Scenario: Both public import paths refer to the same function
- **WHEN** a developer imports `use_theme` from both `webcompy.ui.theme` and `webcompy.ui.composables`
- **THEN** the two imported objects SHALL be the same callable

#### Scenario: Private underscore path is not part of the public API
- **WHEN** a developer writes `from webcompy.ui._composables import use_theme`
- **THEN** the import SHALL fail (the module is not part of the public API)
