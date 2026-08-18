## ADDED Requirements

### Requirement: `ResourcePort` shall provide a `preload()` operation for browser cache priming

`ResourcePort` SHALL provide an async `preload(paths)` operation that primes the client-side caches for the given resource paths without blocking rendering. In the browser, preloading SHALL resolve each resource (from the hydration payload when present, otherwise via the resource endpoint) and retain it so that a later `load_text`/`load_bytes` for the same path completes without a network round trip. On the server, `preload()` SHALL be a no-op. Preload failures SHALL NOT raise to the caller; they SHALL be logged or silently dropped so that prefetching never breaks the app.

#### Scenario: Browser preload primes the cache
- **WHEN** `await port.preload(["documents/a.md"])` completes in the browser
- **AND** a component later calls `await load_text("documents/a.md")`
- **THEN** the content SHALL be served from the primed cache (or hydration payload)
- **AND** no new network request SHALL be issued at load time

#### Scenario: Server preload is a no-op
- **WHEN** `await port.preload(["documents/a.md"])` is called during SSR
- **THEN** it SHALL complete successfully without performing I/O
- **AND** the render context's recorded resources SHALL be unaffected

#### Scenario: Preload failure is non-fatal
- **WHEN** `await port.preload(["documents/missing.md"])` is called in the browser and the resource endpoint returns an error
- **THEN** `preload()` SHALL NOT raise
- **AND** a subsequent `load_text("documents/missing.md")` SHALL raise the usual `ResourceNotFoundError`
