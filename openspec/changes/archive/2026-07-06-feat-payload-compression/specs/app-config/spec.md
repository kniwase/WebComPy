## MODIFIED Requirements

### Requirement: WebComPyAppConfig shall expose compression_threshold for hydration payload compression

`WebComPyAppConfig` SHALL include a `compression_threshold: int | None = 1024` field. The field controls the byte-length threshold above which the SSR/SSG hydration payload SHALL be gzip-compressed before embedding in the HTML. Setting `compression_threshold=None` or `0` SHALL disable compression entirely. The default value (`1024`) preserves the standard compression behavior.

#### Scenario: Default compression threshold
- **WHEN** a developer creates `WebComPyAppConfig()` without specifying `compression_threshold`
- **THEN** `compression_threshold` SHALL default to `1024`
- **AND** the SSR/SSG hydration payload SHALL be compressed when its serialized JSON byte length exceeds 1024 bytes

#### Scenario: Compression disabled by config
- **WHEN** a developer creates `WebComPyAppConfig(compression_threshold=None)`
- **THEN** the SSR/SSG hydration payload SHALL NOT be compressed regardless of size

#### Scenario: Compression disabled by config threshold zero
- **WHEN** a developer creates `WebComPyAppConfig(compression_threshold=0)`
- **THEN** the SSR/SSG hydration payload SHALL NOT be compressed regardless of size

#### Scenario: Custom threshold via config
- **WHEN** a developer creates `WebComPyAppConfig(compression_threshold=4096)`
- **THEN** the SSR/SSG hydration payload SHALL be compressed only when its serialized JSON byte length exceeds 4096 bytes