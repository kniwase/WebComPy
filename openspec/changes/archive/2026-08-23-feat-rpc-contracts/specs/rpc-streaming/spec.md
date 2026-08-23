# RPC Streaming (delta)

## MODIFIED Requirements

### Requirement: Streaming procedures shall register from generator functions with an iterable return annotation

Streaming procedures SHALL register by binding a generator function to a `StreamingProcedure` contract via `ProcedureRegistry.bind` (per the `rpc-contracts` capability), replacing decorator/`register`-style registration. A procedure whose function is a generator function (async generator for `AsyncIterator[T]` / `AsyncIterable[T]` return annotations; sync generator for `Iterator[T]` / `Iterable[T]` return annotations) SHALL register as a streaming procedure. The result schema SHALL be the element type `T` extracted from the subscripted return annotation. Binding SHALL be rejected when the return annotation is unsubscripted (e.g. bare `AsyncIterator`), when a generator function's return annotation is not an iterable annotation, when a non-generator function declares an iterable return annotation, or when the extracted element type does not equal the contract's declared result type. Streaming procedures SHALL share the procedure namespace with ordinary procedures (name collisions rejected as today).

#### Scenario: Async generator registers with element schema
- **WHEN** an async generator function annotated `-> AsyncIterator[Item]` is bound to a `StreamingProcedure` contract declaring `Item`
- **THEN** the procedure SHALL be registered as streaming
- **AND** its result schema SHALL be `Item`

#### Scenario: Sync generator registers
- **WHEN** a generator function annotated `-> Iterator[int]` is bound to a `StreamingProcedure` contract declaring `int`
- **THEN** the procedure SHALL be registered as streaming with element schema `int`

#### Scenario: Unsubscripted iterable return annotation is rejected
- **WHEN** a generator function annotated `-> AsyncIterator` (no type argument) is bound to a `StreamingProcedure` contract
- **THEN** binding SHALL raise an error identifying the missing element type

#### Scenario: Non-generator function with iterable annotation is rejected
- **WHEN** a plain function (not a generator function) annotated `-> Iterator[int]` is bound to a `StreamingProcedure` contract
- **THEN** binding SHALL raise an error stating that streaming procedures require generator functions

#### Scenario: Element type mismatch with the contract is rejected
- **WHEN** a generator function annotated `-> AsyncIterator[Other]` is bound to a `StreamingProcedure` contract declaring a different element type
- **THEN** binding SHALL raise an error naming the element type
