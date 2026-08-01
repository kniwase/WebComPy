## ADDED Requirements

### Requirement: CallbackConsumerNode shall bind to a SignalBase producer

`CallbackConsumerNode` SHALL type its `_producer` field (and its constructor `producer` parameter) as `SignalBase[Any]`, not the broader `SignalNode` base. Callback consumers are created exclusively by `SignalBase.on_before_updating` / `on_after_updating`, which pass `self` (a value-bearing `SignalBase`) as the producer, and `Computed` — the only other producer that participates in dispatch logic — is itself a `Computed(SignalBase[V])`. Because `_dispatch` reads `self._producer._value` (an attribute defined on `SignalBase`, absent on the `SignalNode` base), the declared producer type SHALL be `SignalBase[Any]` so the access is type-valid without a runtime `isinstance` branch or `cast`.

#### Scenario: Dispatch reads the producer value without a type warning
- **WHEN** `CallbackConsumerNode._dispatch` executes and reads `self._producer._value`
- **THEN** `uv run pyright` SHALL report no `reportAttributeAccessIssue` warning
- **AND** no `isinstance(self._producer, SignalBase)` runtime branch SHALL be required to satisfy the type checker

#### Scenario: Producer retyping remains compatible with the signal graph API
- **WHEN** `CallbackConsumerNode.__init__` registers the producer via `producer_add_live_consumer(producer, self)`
- **THEN** the call SHALL remain valid because `SignalBase` is a subclass of `SignalNode`
- **AND** `producer_update_value_version(self._producer)` SHALL remain valid for the same reason

#### Scenario: Computed producer is accepted unchanged
- **WHEN** a `Computed` (which extends `SignalBase[V]`) is the producer of a `CallbackConsumerNode`
- **THEN** the retyped `_producer: SignalBase[Any]` field SHALL accept it without coercion
- **AND** the existing `isinstance(self._producer, Computed)` short-circuit in `_dispatch` SHALL continue to work
