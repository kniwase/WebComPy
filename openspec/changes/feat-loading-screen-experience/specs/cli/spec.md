## ADDED Requirements

### Requirement: Generated HTML shall serialize the loading configuration onto the loading element

Every generated HTML page SHALL serialize the normalized `WebComPyAppConfig.loading` configuration onto the `#webcompy-loading` element as `data-wc-*` attributes (resolved mode, interaction policy, reveal delay, fade-out duration, timeout). When dormant treatment applies, the generated `<body>` element SHALL carry the boot-state class defined by the `loading-screen` capability. These attributes SHALL make the generated HTML self-contained: browser-side loading behavior SHALL be derivable from the DOM alone.

#### Scenario: Default serialization

- **WHEN** a page is generated with default loading configuration
- **THEN** the `#webcompy-loading` element SHALL carry `data-wc-*` attributes reflecting the defaults
- **AND** in `content` mode the `<body>` element SHALL carry the boot-state class

#### Scenario: Custom values serialized

- **WHEN** a page is generated with `loading={"fade_out_ms": 400, "interaction": "inert"}`
- **THEN** the `#webcompy-loading` element attributes SHALL reflect those values

### Requirement: Generated HTML shall include the loading controller script

Every generated HTML page SHALL include an inline classic `<script>` (the loading controller) immediately after the `#webcompy-loading` element. The controller SHALL register `window` listeners for PyScript progress lifecycle events, drive stage labels, sub-status, progress bar, and the stall watchdog, and SHALL be dependency-free. Being a classic script placed before the deferred module script that loads PyScript, it SHALL be guaranteed to observe every boot progress event.

#### Scenario: Controller present in generated HTML

- **WHEN** a generated `index.html` is examined
- **THEN** an inline classic script implementing the loading controller SHALL appear immediately after the `#webcompy-loading` element
- **AND** the controller SHALL NOT be a module script

#### Scenario: Controller present for both dev server and SSG output

- **WHEN** HTML is produced by the dev server SSR handler or by `webcompy generate`
- **THEN** both outputs SHALL include the loading controller

### Requirement: Custom loading templates shall be validated at generation time

When the loading configuration provides a custom `template` (HTML string or file path), HTML generation SHALL validate that the markup contains exactly one element with `id="webcompy-loading"`. If the contract is violated, generation SHALL fail with a clear error. If the template contains none of the documented progress hooks (`data-wc-status`, `data-wc-substatus`, `data-wc-bar`, `data-wc-timeout`), generation SHALL succeed with a warning. A template given as a file path SHALL be resolved relative to the app package directory; a missing file SHALL fail generation with a clear error.

#### Scenario: Valid custom template

- **WHEN** a custom template contains `id="webcompy-loading"` and at least one documented hook
- **THEN** generation SHALL succeed and the generated page SHALL contain the custom markup

#### Scenario: Missing contract ID fails generation

- **WHEN** a custom template lacks `id="webcompy-loading"`
- **THEN** generation SHALL fail with an error naming the missing contract

#### Scenario: Missing template file fails generation

- **WHEN** `template` references a file path that does not exist relative to the app package
- **THEN** generation SHALL fail with an error naming the path
