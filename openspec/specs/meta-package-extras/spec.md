# Meta Package Extras

## Purpose

The `webcompy` core package provides `[project.optional-dependencies]` extras so users can install the full WebComPy stack or subsets with a single `pip install` command. This replaces the need for a separate meta-package.

## Requirements

### Requirement: webcompy[full] shall install all packages

`pip install webcompy[full]` SHALL install `webcompy-server`, `webcompy-cli`, and `webcompy-testing` in addition to core.

#### Scenario: One-command full install
- **WHEN** a user runs `pip install webcompy[full]`
- **THEN** `python -m webcompy start --dev` SHALL work
- **AND** `from webcompy_testing import TestRenderer` SHALL work
- **AND** `from webcompy_server.ports import VirtualDOMNode` SHALL work

### Requirement: webcompy[server] shall install server package

`pip install webcompy[server]` SHALL install only `webcompy-server` (not `webcompy-cli` or `webcompy-testing`).

#### Scenario: Server-only install
- **WHEN** a user runs `pip install webcompy[server]`
- **THEN** `webcompy-server` SHALL be installed
- **AND** `webcompy-cli` and `webcompy-testing` SHALL NOT be installed

### Requirement: webcompy[cli] shall install CLI package

`pip install webcompy[cli]` SHALL install `webcompy-cli`, which transitively installs `webcompy-server`.

#### Scenario: CLI install
- **WHEN** a user runs `pip install webcompy[cli]`
- **THEN** `webcompy-cli` SHALL be installed
- **AND** `python -m webcompy start` SHALL work

### Requirement: webcompy[testing] shall install testing package

`pip install webcompy[testing]` SHALL install `webcompy-testing`, which transitively installs `webcompy-server`.

#### Scenario: Testing install
- **WHEN** a user runs `pip install webcompy[testing]`
- **THEN** `webcompy-testing` SHALL be installed
- **AND** `from webcompy_testing import TestRenderer` SHALL work
