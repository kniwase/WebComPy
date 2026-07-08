## ADDED Requirements

### Requirement: use_state() shall create transferable Signal instances with factory-skip

The framework SHALL provide a `use_state()` composable function importable from `webcompy` and `webcompy.signal`. It SHALL accept a zero-argument factory callable and return a `Signal[T]` instance. On the server (or when no hydration payload is available), the factory SHALL run to produce the initial value. On the browser during hydration, the factory SHALL be skipped if the hydration payload contains a value for this signal's key, and the `Signal` SHALL be created with the restored value.

The function SHALL use `typing.overload` to provide two typed signatures:
1. `use_state(factory: Callable[[], T]) -> Signal[T]` — auto-generated key
2. `use_state(key: str, factory: Callable[[], T]) -> Signal[T]` — explicit key

Direct value arguments (e.g., `use_state(0)`) SHALL NOT be accepted — the first argument MUST be callable. Callable factories that require arguments (e.g., `lambda value: value`) SHALL NOT be accepted; the factory MUST be callable with zero arguments.

#### Scenario: Creating a transferable signal with factory
- **WHEN** a developer writes `count = use_state(lambda: 0)` inside a component setup function
- **THEN** a `Signal[int]` SHALL be returned
- **AND** on the server, the factory `lambda: 0` SHALL run to produce the initial value
- **AND** on the browser during hydration, the factory SHALL be skipped if a transferred value exists

#### Scenario: Creating a transferable signal with explicit key
- **WHEN** a developer writes `count = use_state("counter", lambda: 0)`
- **THEN** the signal SHALL be registered with key `"counter"` for payload matching
- **AND** the key SHALL be used during both collection and restoration

#### Scenario: Factory reads server-only data
- **WHEN** a developer writes `theme = use_state(lambda: inject(COOKIE_PORT_KEY).get("theme", "light"))`
- **THEN** on the server, the factory SHALL read the cookie value
- **AND** the value SHALL be collected and transferred to the browser
- **AND** on the browser during hydration, the factory SHALL be skipped and the transferred value used

#### Scenario: use_state() outside component context
- **WHEN** `use_state(factory)` is called outside a component setup function
- **THEN** the factory SHALL always run (no payload check)
- **AND** a `Signal` SHALL be returned without transfer registration
- **AND** a `UserWarning` SHALL be emitted ("use_state() called outside component setup; signal will not be transferred")
- **AND** no error SHALL be raised

#### Scenario: Type safety with overload
- **WHEN** a developer writes `use_state(0)` (non-callable first argument)
- **THEN** a type checker SHALL report a type error
- **AND** at runtime, a `TypeError` SHALL be raised

#### Scenario: Non-zero-argument factory is rejected
- **WHEN** a developer writes `use_state(lambda value: value)`
- **THEN** a type checker SHALL report a type error
- **AND** at runtime, a `TypeError` SHALL be raised before transfer registration

### Requirement: use_reactive_list() shall create transferable ReactiveList instances with factory-skip

The framework SHALL provide a `use_reactive_list()` composable function importable from `webcompy` and `webcompy.signal`. It SHALL accept a zero-argument factory callable returning a `list[V]` and return a `ReactiveList[V]` instance. The factory-skip mechanism SHALL work identically to `use_state()`: on the server, the factory runs; on the browser during hydration, the factory is skipped if a value exists.

The function SHALL use `typing.overload` to provide two typed signatures:
1. `use_reactive_list(factory: Callable[[], list[V]]) -> ReactiveList[V]` — auto-generated key
2. `use_reactive_list(key: str, factory: Callable[[], list[V]]) -> ReactiveList[V]` — explicit key

#### Scenario: Creating a transferable reactive list
- **WHEN** a developer writes `items = use_reactive_list(lambda: [1, 2, 3])` inside a component setup function
- **THEN** a `ReactiveList[int]` SHALL be returned
- **AND** the returned instance SHALL support mutation methods (`append`, `pop`, etc.) that trigger change events
- **AND** on the browser during hydration, the factory SHALL be skipped if a transferred value exists

#### Scenario: Mutations on a transferred ReactiveList
- **WHEN** a `ReactiveList` was created via `use_reactive_list()` with a restored value
- **AND** the developer calls `items.append(4)`
- **THEN** the change event SHALL fire normally
- **AND** `on_after_updating` callbacks SHALL be notified

#### Scenario: use_reactive_list() outside component context
- **WHEN** `use_reactive_list(factory)` is called outside a component setup function
- **THEN** the factory SHALL always run (no payload check)
- **AND** a `ReactiveList` SHALL be returned without transfer registration
- **AND** a `UserWarning` SHALL be emitted
- **AND** no error SHALL be raised

### Requirement: use_reactive_dict() shall create transferable ReactiveDict instances with factory-skip

The framework SHALL provide a `use_reactive_dict()` composable function importable from `webcompy` and `webcompy.signal`. It SHALL accept a zero-argument factory callable returning a `dict[K, V]` and return a `ReactiveDict[K, V]` instance. The factory-skip mechanism SHALL work identically to `use_state()`.

The function SHALL use `typing.overload` to provide two typed signatures:
1. `use_reactive_dict(factory: Callable[[], dict[K, V]]) -> ReactiveDict[K, V]` — auto-generated key
2. `use_reactive_dict(key: str, factory: Callable[[], dict[K, V]]) -> ReactiveDict[K, V]` — explicit key

#### Scenario: Creating a transferable reactive dict
- **WHEN** a developer writes `settings = use_reactive_dict(lambda: {"theme": "dark"})` inside a component setup function
- **THEN** a `ReactiveDict[str, str]` SHALL be returned
- **AND** the returned instance SHALL support mutation methods (`__setitem__`, `pop`, etc.) that trigger change events
- **AND** on the browser during hydration, the factory SHALL be skipped if a transferred value exists

#### Scenario: use_reactive_dict() outside component context
- **WHEN** `use_reactive_dict(factory)` is called outside a component setup function
- **THEN** the factory SHALL always run (no payload check)
- **AND** a `ReactiveDict` SHALL be returned without transfer registration
- **AND** a `UserWarning` SHALL be emitted
- **AND** no error SHALL be raised

### Requirement: Composable auto-key shall use caller source location

When the `key` parameter is omitted, all composables (`use_state()`, `use_reactive_list()`, `use_reactive_dict()`) SHALL generate a key from the caller's source location using `inspect.currentframe()` and `dis.get_instructions()`. The key format SHALL be `"{filename}:{start_line}:{start_col}"` (Python 3.12+ positions API). If the positions API is unavailable, the fallback format SHALL be `"{filename}:{lineno}"`. The key SHALL be stable across server and browser environments (same source file and line).

#### Scenario: Auto-key from source location
- **WHEN** `use_state(lambda: 0)` is called at `my_component.py:10:14`
- **THEN** the generated key SHALL be `"my_component.py:10:14"`
- **AND** the same key SHALL be generated on both server and browser

#### Scenario: Same-line calls get distinct keys
- **WHEN** two `use_state()` calls appear on the same source line
- **THEN** the column number SHALL disambiguate them
- **AND** each call SHALL get a distinct key

#### Scenario: Fallback when positions API unavailable
- **WHEN** `dis.get_instructions()` or `instr.positions` is not available (e.g., limited runtime)
- **THEN** the fallback key format SHALL be `"{filename}:{lineno}"`
- **AND** same-line calls SHALL share a key (user SHALL use explicit key to disambiguate)

### Requirement: Signal() direct construction shall emit UserWarning

`Signal.__init__()` SHALL emit a `UserWarning` with the message "Direct Signal() construction bypasses SSR transfer. Use use_state(factory) instead." when called directly by user code. The `Signal` class SHALL remain as the return type of `use_state()` and for type annotations.

Internal `Signal._create(value)`, `ReactiveList._create(value)`, and `ReactiveDict._create(value)` classmethods SHALL bypass warnings by using `object.__new__()` + parent `__init__()`. The composables and other framework internals SHALL use these `_create()` methods exclusively.

#### Scenario: UserWarning on direct construction
- **WHEN** user code calls `Signal(0)` directly
- **THEN** a `UserWarning` SHALL be emitted
- **AND** the `Signal` SHALL still be created and function normally

#### Scenario: No warning from composables
- **WHEN** `use_state(lambda: 0)` creates a `Signal` internally
- **THEN** no `UserWarning` SHALL be emitted
- **AND** `Signal._create()` SHALL be used instead of `Signal()`

#### Scenario: Signal type annotation still works
- **WHEN** a developer writes `count: Signal[int] = use_state(lambda: 0)`
- **THEN** the type annotation SHALL be valid
- **AND** `Signal` SHALL remain importable from `webcompy.signal`
