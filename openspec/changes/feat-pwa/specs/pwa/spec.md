# PWA Specification (delta)

## ADDED Requirements

### Requirement: PWA support shall be declarative and disabled by default

The build configuration SHALL provide a `PWAConfig` (under the build/server configuration) with an `enabled` flag defaulting to false. When disabled, no manifest, Service Worker, registration script, or related injection SHALL be produced. Enabling PWA SHALL require no user JavaScript.

#### Scenario: Disabled by default

- **WHEN** an application builds without PWA configuration
- **THEN** the output SHALL contain no Service Worker, no manifest link, and no registration script

### Requirement: The Web App Manifest shall be generated, served, and linked

When PWA is enabled, `ManifestConfig` (name, short_name, icons, display, theme_color, background_color, start_url and scope defaulting from the app base URL) SHALL be serialized to `manifest.webmanifest`, emitted into static output and served by the server at a stable path, and the document builder SHALL inject `<link rel="manifest">` into the head of rendered pages. The manifest SHALL be emitted and served at the path `manifest.webmanifest` relative to the application base URL with the `application/manifest+json` media type.

#### Scenario: Manifest reaches the page

- **WHEN** a PWA-enabled application is served or generated
- **THEN** the page head SHALL contain the manifest link
- **AND** fetching the manifest path SHALL return the serialized ManifestConfig with start_url and scope resolved from the base URL

### Requirement: The Service Worker shall be generated at build time from a framework-owned template

The framework SHALL ship a Service Worker template implementing precaching, strategy dispatch, cache cleanup, and offline fallback. At build time the effective PWA configuration (precache manifest, runtime rules, fallback path, versioned cache names) SHALL be embedded into the template and `sw.js` emitted into the output. When served dynamically, the worker SHALL be delivered at the path `sw.js` relative to the application base URL with the `application/javascript` media type and `Cache-Control: no-cache` response headers. Users SHALL NOT write or supply Service Worker code in v1, and no third-party Service Worker library SHALL be required.

#### Scenario: Generated worker carries the build configuration

- **WHEN** a PWA-enabled application builds with runtime rules configured
- **THEN** the emitted `sw.js` SHALL contain the serialized configuration and implement precache install, fetch dispatch, and activate cleanup without external fetches

### Requirement: Precache shall enumerate build output automatically with runtime precache opt-in

The `precache` setting SHALL accept `"auto"` (the default) and `"none"`. `precache="auto"` SHALL enumerate the build output (generated pages and emitted assets) into the precache manifest, and SHALL include each generated page's clean URL alongside its `index.html` file path so navigation requests match cached entries. `precache="none"` SHALL produce an empty precache manifest without enumerating build output. Precaching the Python runtime (interpreter/PyScript bundles) SHALL be opt-in via `precache_runtime`: runtime files SHALL be excluded from automatic enumeration regardless of how the runtime is served, and enabling the option SHALL log a build-time warning stating the approximate storage cost. For local runtime serving, enabling `precache_runtime` SHALL include the runtime files in the precache manifest and the warning SHALL state the summed size of those files. For CDN runtime serving, enabling `precache_runtime` SHALL include the known runtime entry file URLs (PyScript core and the Pyodide lock file) with a warning that offline startup is not guaranteed; transitive CDN runtime enumeration is out of scope. Combining `precache="none"` with `precache_runtime` SHALL be rejected as an invalid configuration. Assets with content-hashed names SHALL be considered cache-first safe by construction.

#### Scenario: Auto precache covers build output

- **WHEN** a PWA-enabled SSG build completes
- **THEN** the precache manifest SHALL include the generated pages and emitted assets
- **AND** the Python runtime SHALL be excluded unless explicitly opted in

#### Scenario: Precache disabled

- **WHEN** a PWA-enabled build sets `precache="none"`
- **THEN** the precache manifest SHALL be empty
- **AND** the build SHALL NOT enumerate the output directory

#### Scenario: Offline navigation to a generated page serves its cached index

- **WHEN** an offline user navigates to the URL of a generated page (for example `/documents/foo/`)
- **THEN** the Service Worker SHALL serve the page's precached `index.html` response rather than the offline fallback

#### Scenario: Runtime precache warns about size

- **WHEN** runtime precaching is enabled
- **THEN** the build SHALL log a warning stating the approximate storage cost

### Requirement: Runtime caching shall follow explicit pattern rules with three strategies

Runtime rules SHALL match requests by URL pattern (prefix or glob) and apply one of `cache-first`, `network-first`, or `stale-while-revalidate`, with optional max-entries and max-age eviction. Runtime rules SHALL apply to same-origin requests only; cross-origin requests SHALL pass through without implicit caching. Requests matching no rule SHALL pass through to the network without implicit caching. Entries stored by a runtime rule SHALL be kept in a cache isolated from the precache, and max-entries eviction SHALL affect only the matching rule's cache.

#### Scenario: network-first rule serves fresh data with offline fallback to cache

- **WHEN** a runtime rule matches `/api/` with `network-first` and the network is unavailable
- **THEN** the cached response for the request SHALL be served if present

### Requirement: Worker updates shall activate immediately and clean old caches

The generated worker SHALL call `skipWaiting` on install and `clientsClaim` on activate. Cache storage names SHALL include the build version, and the activate step SHALL delete caches belonging to previous versions. Precache install SHALL be resilient: a failure to fetch an individual entry SHALL be logged and SHALL NOT fail the install event.

#### Scenario: New deployment replaces caches

- **WHEN** a new build deploys and its worker activates
- **THEN** the new version SHALL take control of clients immediately
- **AND** caches from previous versions SHALL be deleted

### Requirement: Offline navigation shall serve a fallback page

Navigation requests that fail while offline and match no precached entry SHALL respond with a configured fallback page; the framework SHALL provide a default minimal offline page embedded in the worker, overridable by path (the override file SHALL be added to the precache manifest when configured). The fallback response SHALL be served with a successful (2xx) status and a header identifying it as the offline fallback.

#### Scenario: Offline navigation shows the fallback

- **WHEN** the user navigates to a non-precached page while offline
- **THEN** the fallback page SHALL be served with a successful status instead of a network error

### Requirement: Registration shall be injected with the correct scope and dev mode shall stay safe

When PWA is enabled, the document builder SHALL inject a registration script registering `sw.js` scoped to the application base URL (including prefixed/embedded deployments). In dev mode the Service Worker SHALL be disabled by default (no generation or registration) to avoid interference with hot reload; explicit enablement SHALL be possible.

#### Scenario: Registration respects base URL

- **WHEN** a PWA-enabled app is served under a base URL prefix
- **THEN** the registration script SHALL register the worker at that prefix scope

#### Scenario: Dev mode does not register a worker

- **WHEN** the dev server runs with default settings
- **THEN** no Service Worker SHALL be generated or registered
