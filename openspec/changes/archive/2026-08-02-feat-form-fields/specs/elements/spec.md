# Delta: elements

## ADDED Requirements

### Requirement: `:bind` shall accept Field objects

In addition to a writable `Signal`, the `:bind` attribute SHALL accept a `webcompy.forms.Field` instance. The binding SHALL use `field.value` as the bound signal with all per-element rules and conversions unchanged, SHALL set `field.dirty` to `True` on each write-back (before the value update), and SHALL register a `blur` handler setting `field.touched` to `True` (chained before any user `blur` handler). Type-discipline validation SHALL apply to `field.value` exactly as it does to a directly-passed `Signal`.

#### Scenario: Field accepted on text input
- **WHEN** `html.INPUT({":bind": field})` is used with a `Field` wrapping `Signal("")`
- **THEN** the input SHALL two-way-bind `field.value` exactly as if the Signal were passed directly

#### Scenario: Interaction state wiring
- **WHEN** a user types in a `:bind`-bound Field input and then blurs
- **THEN** `field.dirty.value` SHALL be `True` after the first keystroke
- **AND** `field.touched.value` SHALL be `True` after the blur

#### Scenario: Field type discipline
- **WHEN** `html.INPUT({"type": "checkbox", ":bind": field})` is used with a `Field` wrapping a non-`bool` Signal
- **THEN** `WebComPyException` SHALL be raised naming the required type
