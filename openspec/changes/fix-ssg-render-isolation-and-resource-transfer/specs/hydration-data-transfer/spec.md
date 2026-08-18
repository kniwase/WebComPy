## MODIFIED Requirements

### Requirement: SSR shall populate payload.resources from ServerResourcePort

During SSR/SSG, after component rendering completes for a request, `ServerRenderContext` SHALL collect the recorded resources from the current render context's `ServerResourcePort` (via `port.get_recorded_resources()`) and populate `TransferPayload.resources` with the path → bytes mapping. Recorded resources SHALL be scoped to the render context: resources loaded while generating other pages or serving other requests SHALL NOT appear. The codec pipeline SHALL base64-encode the bytes prior to JSON serialization.

#### Scenario: Loaded resource appears in hydration payload
- **WHEN** an async component in an SSR'd page calls `await load_text("templates/card.html")`
- **AND** the resource file exists
- **THEN** the resulting `__webcompy_data__` script SHALL include `"templates/card.html"` in the `resources` dict
- **AND** the value SHALL be the base64 of the file's bytes

#### Scenario: Failed load does not appear in payload
- **WHEN** a component calls `await load_text("missing.html")` and the load raises
- **THEN** the `resources` dict SHALL NOT contain `"missing.html"` after SSR

#### Scenario: Same resource loaded twice appears once in payload
- **WHEN** two components call `await load_text("templates/card.html")` during the same SSR pass
- **THEN** the `resources` dict SHALL contain a single entry for `"templates/card.html"` with the latest content

#### Scenario: Previously generated page's resources do not leak
- **WHEN** SSG generates page A (loading `documents/a.md`) and then page B (loading `documents/b.md`)
- **THEN** page B's payload `resources` SHALL contain `"documents/b.md"` but NOT `"documents/a.md"` (in the default per-context transfer mode)
- **AND** page A's payload SHALL contain `"documents/a.md"` only

## ADDED Requirements

### Requirement: SSG SHALL support an opt-in full text-resource transfer mode

Static site generation SHALL support an opt-in mode in which every allow-listed text resource is embedded in every generated page's transfer payload, regardless of which resources the page itself loaded. In this mode, client-side navigation SHALL NOT issue resource fetches for allow-listed text resources, because the browser port resolves them from the payload. Text resources SHALL be identified by an extension allowlist (e.g., `.md`, `.txt`, `.json`, `.csv`, `.yaml`, `.yml`, `.toml`, `.svg`), and binary resources SHALL be excluded. The mode and its text-resource classification SHALL be configurable via the build configuration; the default mode SHALL remain per-context ("used") transfer.

#### Scenario: Full text-resource transfer enabled
- **WHEN** SSG runs with the full text-resource transfer mode enabled
- **AND** the resource allow-list contains `documents/a.md` through `documents/z.md`
- **THEN** every generated page's payload SHALL contain all of those markdown resources
- **AND** the output SHALL be identical regardless of route generation order

#### Scenario: Navigation issues no resource fetch in full-transfer mode
- **WHEN** a user lands on any generated page of a site built with the full text-resource transfer mode
- **AND** navigates client-side to another page whose component loads an allow-listed text resource
- **THEN** the resource SHALL resolve from the transferred payload or browser cache
- **AND** no request to the resource endpoint SHALL be issued

#### Scenario: Binary resources are excluded from full transfer
- **WHEN** the resource allow-list contains `assets/logo.png`
- **AND** the full text-resource transfer mode is enabled
- **THEN** generated payloads SHALL NOT contain `assets/logo.png`
