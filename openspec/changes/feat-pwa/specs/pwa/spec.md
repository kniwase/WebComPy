# PWA Specification (delta)

## ADDED Requirements

### Requirement: PWA support shall be declarative and disabled by default

The build configuration SHALL provide a `PWAConfig` (under the build/server configuration) with an `enabled` flag defaulting to false. When disabled, no manifest, Service Worker, registration script, or related injection SHALL be produced. Enabling PWA SHALL require no user JavaScript.

#### Scenario: Disabled by default

- **WHEN** an application builds without PWA configuration
- **THEN** the output SHALL contain no Service Worker, no manifest link, and no registration script

### Requirement: The Web App Manifest shall be generated, served, and linked

When PWA is enabled, `ManifestConfig` (name, short_name, icons, display, theme_color, background_color, start_url and scope defaulting from the app base URL) SHALL be serialized to `manifest.webmanifest`, emitted into static output and served by the server at a stable path, and the document builder SHALL inject `<link rel="manifest">` into the head of rendered pages.

#### Scenario: Manifest reaches the page

- **WHEN** a PWA-enabled application is served or generated
- **THEN** the page head SHALL contain the manifest link
- **AND** fetching the manifest path SHALL return the serialized ManifestConfig with start_url and scope resolved from the base URL

### Requirement: The Service Worker shall be generated at build time from a framework-owned template

The framework SHALL ship a Service Worker template implementing precaching, strategy dispatch, cache cleanup, and offline fallback. At build time the effective PWA configuration (precache manifest, runtime rules, fallback path, versioned cache names) SHALL be embedded into the template and `sw.js` emitted into the output. Users SHALL NOT write or supply Service Worker code in v1, and no third-party Service Worker library SHALL be required.

#### Scenario: Generated worker carries the build configuration

- **WHEN** a PWA-enabled application builds with runtime rules configured
- **THEN** the emitted `sw.js` SHALL contain the serialized configuration and implement precache install, fetch dispatch, and activate cleanup without external fetches

### Requirement: Precache shall enumerate build output automatically with runtime precache opt-in

`precache="auto"` SHALL enumerate the build output (generated pages and emitted assets) into the precache manifest. Precaching the Python runtime (interpreter/PyScript bundles) SHALL be opt-in, and enabling it SHALL log a build-time size warning. Assets with content-hashed names SHALL be considered cache-first safe by construction.

#### Scenario: Auto precache covers build output

- **WHEN** a PWA-enabled SSG build completes
- **THEN** the precache manifest SHALL include the generated pages and emitted assets
- **AND** the Python runtime SHALL be excluded unless explicitly opted in

#### Scenario: Runtime precache warns about size

- **WHEN** runtime precaching is enabled
- **THEN** the build SHALL log a warning stating the approximate storage cost

### Requirement: Runtime caching shall follow explicit pattern rules with three strategies

Runtime rules SHALL match requests by URL pattern (prefix or glob) and apply one of `cache-first`, `network-first`, or `stale-while-revalidate`, with optional max-entries and max-age eviction. Requests matching no rule SHALL pass through to the network without implicit caching.

#### Scenario: network-first rule serves fresh data with offline fallback to cache

- **WHEN** a runtime rule matches `/api/` with `network-first` and the network is unavailable
- **THEN** the cached response for the request SHALL be served if present

### Requirement: Worker updates shall activate immediately and clean old caches

The generated worker SHALL call `skipWaiting` on install and `clientsClaim` on activate. Cache storage names SHALL include the build version, and the activate step SHALL delete caches belonging to previous versions.

#### Scenario: New deployment replaces caches

- **WHEN** a new build deploys and its worker activates
- **THEN** the new version SHALL take control of clients immediately
- **AND** caches from previous versions SHALL be deleted

### Requirement: Offline navigation shall serve a fallback page

Navigation requests that fail while offline and match no precached entry SHALL respond with a configured fallback page; the framework SHALL provide a default minimal offline page, overridable by path.

#### Scenario: Offline navigation shows the fallback

- **WHEN** the user navigates to a non-precached page while offline
- **THEN** the fallback page SHALL be served instead of a network error

### Requirement: Registration shall be injected with the correct scope and dev mode shall stay safe

When PWA is enabled, the document builder SHALL inject a registration script registering `sw.js` scoped to the application base URL (including prefixed/embedded deployments). In dev mode the Service Worker SHALL be disabled by default (no generation or registration) to avoid interference with hot reload; explicit enablement SHALL be possible.

#### Scenario: Registration respects base URL

- **WHEN** a PWA-enabled app is served under a base URL prefix
- **THEN** the registration script SHALL register the worker at that prefix scope

#### Scenario: Dev mode does not register a worker

- **WHEN** the dev server runs with default settings
- **THEN** no Service Worker SHALL be generated or registered
