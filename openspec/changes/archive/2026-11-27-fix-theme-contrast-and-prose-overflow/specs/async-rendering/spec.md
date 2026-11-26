# Spec Delta

## MODIFIED Requirements

### Requirement: Hydration mismatch records shall be aggregated and exposed

After the hydration pass and the drain complete, the app SHALL aggregate the mismatch records collected at the element level (see the elements capability). The hydration window SHALL be closed before the aggregated warning is emitted, so records and summary can never diverge: records produced by signal-triggered renders after the drain (e.g. during the loading fade, while the page is already interactive) SHALL NOT be appended after the summary was taken. If records exist, exactly ONE console warning SHALL be emitted through `webcompy.logging.warn` (which logs to `window.console.warn` rather than stdlib `logging`/stderr so PyScript does not render a `.py-error` DOM banner), summarizing the mismatch count by class (text, attribute, tag, node-count) and by owning component ID. If no records exist, no hydration-mismatch message SHALL be logged. `RenderContext` SHALL expose a `hydration_report` attribute containing the full records (class, expected value, actual value, owning component ID each) for tests and tooling; it SHALL be an empty collection when hydration produced no mismatches, and SHALL be unavailable/empty before hydration runs.

#### Scenario: Matching hydration produces no warning

- **WHEN** browser hydration of an SSR page completes without mismatches
- **THEN** no hydration-mismatch warning SHALL be logged
- **AND** `RenderContext.hydration_report` SHALL be empty

#### Scenario: Mismatching hydration produces a single aggregated warning

- **WHEN** browser hydration produces mismatches in several elements of one or more components
- **THEN** a single console warning SHALL summarize the mismatch counts by class and component via browser `console.warn`
- **AND** no `<div class="py-error">` stderr banner SHALL be injected into the visible DOM
- **AND** `RenderContext.hydration_report` SHALL contain one record per mismatch with class, expected, actual, and component ID

#### Scenario: The summary is emitted only after the hydration window closes

- **WHEN** the hydration drain has completed and the loading fade begins
- **THEN** the aggregated warning SHALL be emitted only after the hydration window is closed
- **AND** any `record_mismatch` call made after the window closes (e.g. by a signal-triggered render during the fade) SHALL be a no-op, so the reported records and the single warning can never diverge

#### Scenario: Report available before hydration is empty

- **WHEN** `RenderContext.hydration_report` is read before the hydration pass has run (or on the server)
- **THEN** it SHALL be an empty collection
