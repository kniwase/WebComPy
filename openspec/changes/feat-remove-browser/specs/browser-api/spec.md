## MODIFIED Requirements

### Requirement: browser public export removed
The `browser` public export from `webcomppy` SHALL be removed. The browser object definition SHALL be relocated to `webcompy/ports/_browser/_raw.py` as an internal implementation detail.

#### Scenario: public browser import raises AttributeError
- **WHEN** code attempts `from webcompy import browser`
- **THEN** Python SHALL raise `AttributeError`

#### Scenario: Internal browser object accessible for port implementations
- **WHEN** port implementations under `ports/_browser/` access the raw browser object
- **THEN** they SHALL import from `webcompy.ports._browser._raw`

#### Scenario: _browser/_modules.py preserved as re-export stub
- **WHEN** Router files (to be migrated in phase 6) import from `webcompy._browser._modules`
- **THEN** the import SHALL succeed via a thin re-export stub delegating to `webcompy.ports._browser._raw`
