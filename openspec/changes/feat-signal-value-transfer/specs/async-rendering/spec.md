## ADDED Requirements

### Requirement: Signal value collection shall occur after await_pending completes

During SSR/SSG, `collect_transfer_data(root)` SHALL be called after `await scheduler.await_pending()` completes and before `ctx.dispose()`. This ensures that any Signal values modified by async-resolved tasks (e.g., `AsyncResult` callbacks that set Signal values) are captured in their final state.

#### Scenario: Collection timing relative to scheduler drain
- **WHEN** the SSR pipeline runs `generate_html()` or the ASGI handler processes a request
- **THEN** the call order SHALL be: `await ctx._root._render()` → `await scheduler.await_pending()` → `collect_transfer_data(root)` → `ctx.dispose()`
- **AND** Signal values modified during `await_pending()` SHALL be reflected in the collected payload
