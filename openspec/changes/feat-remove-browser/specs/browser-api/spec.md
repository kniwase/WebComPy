## MODIFIED Requirements

### Requirement: browser object removed
The `browser` object and `webcompy/_browser/` directory SHALL be removed. All browser API access SHALL go through port ABCs.

#### Scenario: browser import raises ImportError
- **WHEN** code attempts `from webcompy._browser._modules import browser`
- **THEN** Python SHALL raise `ImportError`

#### Scenario: Ports remain functional
- **WHEN** `browser` is removed
- **THEN** all existing framework functionality SHALL continue to work through port injection
