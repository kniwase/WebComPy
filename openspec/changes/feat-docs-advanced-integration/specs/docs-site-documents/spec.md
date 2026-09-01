# Delta: docs-site-documents

## ADDED Requirements

### Requirement: The Architecture & Integration block shall exist

The Advanced Usage category SHALL contain a `group` "Architecture & Integration" holding, in order: `dependency-injection-deep-dive`, `middleware`, `routing-deep-dive`, `plugins`, `typed-api-deep-dive`, `ui-headless-contract`, `custom-elements`, `persistence-patterns`. Each page SHALL follow the Advanced structure and every Basic page whose topic splits into it SHALL back-link (target existence is validated by the existing body cross-link scan).

#### Scenario: Split-policy links complete

- **WHEN** a Basic routing/forms/DI/storage page is read
- **THEN** its Next steps links to the corresponding Architecture & Integration page, and that page links back
