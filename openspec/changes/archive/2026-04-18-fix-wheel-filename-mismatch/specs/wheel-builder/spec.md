## MODIFIED Requirements

### Requirement: The wheel builder shall support bundling multiple packages into a single wheel

The wheel builder SHALL be able to bundle multiple top-level packages (e.g., the webcompy framework and a user application) into a single wheel. The bundled wheel SHALL list all top-level packages in `top_level.txt`. Both packages SHALL be importable after PyScript loads the wheel. The wheel filename SHALL be derived from the app package name using PEP 427 normalization, and a helper function SHALL compute this filename for use by all consumers.

#### Scenario: Bundling framework and application

- **WHEN** the CLI builds a bundled wheel containing `webcompy` and `myapp` packages
- **THEN** the `.dist-info/top_level.txt` SHALL contain both `webcompy` and `myapp`
- **AND** `import webcompy` SHALL work after the wheel is installed
- **AND** `import myapp` SHALL work after the wheel is installed
- **AND** only a single `.whl` file SHALL be produced

#### Scenario: Bundled wheel naming

- **WHEN** the CLI builds a bundled wheel for an app package named `docs_src` with version `25.107.43200`
- **THEN** the wheel file name SHALL be `docs-src-25.107.43200-py3-none-any.whl`
- **AND** `get_wheel_filename("docs_src", "25.107.43200")` SHALL return `"docs-src-25.107.43200-py3-none-any.whl"`
- **AND** the filename SHALL match the URL referenced in the generated HTML

#### Scenario: Wheel filename consistency across all consumers

- **WHEN** the HTML template, dev server, and static generator each need the wheel filename
- **THEN** they SHALL all call `get_wheel_filename(name, version)` from the wheel builder module
- **AND** no consumer SHALL hardcode the wheel filename pattern