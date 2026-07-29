# Delta: async-scheduler

## MODIFIED Requirements

### Requirement: No bare asyncio scheduling shall exist outside AsyncSchedulerPort

The framework codebase SHALL NOT contain direct `asyncio.ensure_future()` or `asyncio.get_event_loop().create_task()` calls in the `webcompy`, `webcompy-server`, or `webcompy-cli` packages, except within `AsyncSchedulerPort` implementations and the `aio_run` fallback path. All async task scheduling SHALL route through `AsyncSchedulerPort.schedule()` or `aio_run()`. This invariant SHALL be enforced by CI review.

#### Scenario: Code review detects bare ensure_future
- **WHEN** a pull request introduces a new `asyncio.ensure_future()` call outside `AsyncSchedulerPort` implementations or `aio_run`
- **THEN** the CI review SHALL flag it as an invariant violation
