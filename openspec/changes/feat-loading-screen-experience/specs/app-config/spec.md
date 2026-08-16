## ADDED Requirements

### Requirement: WebComPyAppConfig shall accept a loading configuration dict

`WebComPyAppConfig` SHALL accept an optional `loading: dict | None` field (default `None`). When provided, the dict SHALL be normalized and validated in `__post_init__` following the same pattern as the `theme` field. Recognized keys SHALL be: `mode` (`"auto"`, `"overlay"`, or `"content"`, default `"auto"`), `interaction` (`"block"`, `"inert"`, or `"passthrough"`, default `"block"`), `stages` (`bool`, default `True`), `dormant` (`bool`, default `True`), `messages` (`dict[str, str]` mapping stage keys defined by the `loading-screen` capability to display labels, default `{}`), `template` (preset name, HTML string, or app-package-relative file path; default `None`), `reveal_delay_ms` (`int` from 0 to 10000, default `350`), `fade_out_ms` (`int` from 0 to 10000, default `250`), and `timeout_seconds` (`int` from 0 to 3600, default `30`, where `0` disables the watchdog). Invalid keys, invalid value types, or out-of-range values SHALL raise a `TypeError` or `ValueError` at config construction time. The `loading` field SHALL be browser-relevant configuration importable from `webcompy.app` without server-only imports.

#### Scenario: Default loading configuration

- **WHEN** a developer creates `WebComPyAppConfig(loading={})`
- **THEN** `loading` SHALL normalize to the documented defaults (mode `"auto"`, interaction `"block"`, stages `True`, dormant `True`, reveal delay 350ms, fade-out 250ms, timeout 30s)

#### Scenario: Configuring content mode with passthrough interaction

- **WHEN** a developer creates `WebComPyAppConfig(loading={"mode": "content", "interaction": "passthrough"})`
- **THEN** the normalized config SHALL retain those values
- **AND** unset keys SHALL receive their defaults

#### Scenario: Invalid mode rejected

- **WHEN** a developer creates `WebComPyAppConfig(loading={"mode": "fancy"})`
- **THEN** a `ValueError` SHALL be raised

#### Scenario: Invalid key rejected

- **WHEN** a developer creates `WebComPyAppConfig(loading={"spinner": True})`
- **THEN** a `ValueError` SHALL be raised identifying the unknown key

#### Scenario: Invalid value type rejected

- **WHEN** a developer creates `WebComPyAppConfig(loading={"fade_out_ms": "250"})`
- **THEN** a `TypeError` SHALL be raised

#### Scenario: Invalid dormant type rejected

- **WHEN** a developer creates `WebComPyAppConfig(loading={"dormant": "yes"})`
- **THEN** a `TypeError` SHALL be raised
