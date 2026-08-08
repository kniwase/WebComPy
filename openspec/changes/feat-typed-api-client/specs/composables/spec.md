# Delta Spec: composables

## ADDED Requirements

### Requirement: use_async_result shall support opting out of hydration transfer
`use_async_result` SHALL accept a `transfer: bool = True` parameter. With `transfer=True` (default), the resolved result SHALL be recorded into the hydration transfer payload during SSR/SSG as today. With `transfer=False`, the result SHALL NOT be recorded into the transfer payload: during SSR/SSG the fetch still executes (the page needs its content), but the resolved data SHALL NOT be persisted into the generated HTML; in the browser, hydration finds no transferred entry and the fetch executes on the client. `transfer=False` governs persistence only — it does NOT prevent build-time execution (components requiring no build-time execution SHALL use `ClientOnly`).

#### Scenario: Default behavior unchanged
- **WHEN** `use_async_result(fetcher)` is called without `transfer`
- **THEN** the resolved result SHALL be included in the hydration transfer payload during SSR as before this change

#### Scenario: transfer=False excludes data from the payload
- **WHEN** `use_async_result(fetcher, transfer=False)` is rendered during SSR or SSG
- **THEN** the fetch SHALL execute for rendering
- **AND** the hydration payload embedded in the HTML SHALL NOT contain the result
- **AND** after hydration in the browser the fetcher SHALL execute client-side

#### Scenario: Sensitive data is not baked into static artifacts
- **WHEN** a page generated via SSG uses `use_async_result(fetcher, transfer=False)` for user-specific data
- **THEN** the generated HTML files SHALL NOT contain that data in their hydration payloads
