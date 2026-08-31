# Template Engine Specification (delta)

## ADDED Requirements

### Requirement: Interpolation shall register signal reads made inside called functions

The interpolation binder SHALL treat an expression as reactive when any Signal is read during its evaluation, including reads that occur inside a function the expression calls (e.g. `{{ t("nav.home") }}` where `t` reads a locale Signal). Such interpolations SHALL re-evaluate when a read Signal changes. Expressions that read no Signal SHALL remain statically bound.

#### Scenario: Function-call interpolation is reactive

- **WHEN** a template renders `{{ t("nav.home") }}` where `t` reads a `Signal[str]` and returns a message, and the Signal value changes
- **THEN** the rendered text SHALL update to the new message without a manual refresh

#### Scenario: Signal-free expressions stay static

- **WHEN** a template renders `{{ compute() }}` where `compute` reads no Signal
- **THEN** the interpolation SHALL remain statically bound (no Computed wrapper)