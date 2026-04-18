## MODIFIED Requirements

### Requirement: Python packages shall be delivered to the browser via wheels
The framework SHALL package itself and the application as a single bundled Python wheel. PyScript SHALL load this wheel in the browser, enabling the entire application — framework and user code alike — to run as standard Python without a JavaScript build step.

#### Scenario: Loading an application in the browser
- **WHEN** a user opens a WebComPy application in their browser
- **THEN** PyScript SHALL load a single bundled wheel containing both the webcompy framework and the application
- **AND** both `import webcompy` and the application import SHALL work
- **AND** no custom JavaScript build step SHALL be required
- **AND** no `typing_extensions` dependency SHALL be required