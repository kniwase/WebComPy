## ADDED Requirements

### Requirement: signal() shall create transferable Signal instances with factory-skip

The framework SHALL provide a `signal()` composable function importable from `webcompy` and `webcompy.signal`. It SHALL accept a factory callable and return a `Signal[T]` instance. On the server (or when no hydration payload is available), the factory SHALL run to produce the initial value. On the browser during hydration, the factory SHALL be skipped if the hydration payload contains a value for this signal's key, and the `Signal` SHALL be created with the restored value.

The function SHALL use `typing.overload` to provide two typed signatures:
1. `signal(factory: Callable[[], T]) -> Signal[T]` — auto-generated key
2. `signal(key: str, factory: Callable[[, T]) -> Signal[T]` — explicit key

Direct value arguments (e.g., `signal(0)`) SHALL NOT be accepted — the first argument MUST be callable.

#### Scenario: Creating a transferable signal with factory
- **WHEN** a developer writes `count = signal(lambda: 0)` inside a component setup function
- **THEN** a `Signal[int]` SHALL be returned
- **AND** on the server, the factory `lambda: 0` SHALL run to produce the initial value
- **AND** on the browser during hydration, the factory SHALL be skipped if a transferred value exists

#### Scenario: Creating a transferable signal with explicit key
- **WHEN** a developer writes `count = signal("counter", lambda: 0)`
- **THEN** the signal SHALL be registered with key `"counter"` for payload matching
- **AND** the key SHALL be used during both collection and restoration

#### Scenario: Factory reads server-only data
- **WHEN** a developer writes `theme = signal(lambda: inject(COOKIE_PORT_KEY).get("theme", "light"))`
- **THEN** on the server, the factory SHALL read the cookie value
- **AND** the value SHALL be collected and transferred to the browser
- **AND** on the browser during hydration, the factory SHALL be skipped and the transferred value used

#### Scenario: signal() outside component context
- **WHEN** `signal(factory)` is called outside a component setup function
- **THEN** the factory SHALL always run (no payload check)
- **AND** a `Signal` SHALL be returned without transfer registration
- **AND** no error SHALL be raised

#### Scenario: Type safety with overload
- **WHEN** a developer writes `signal(0)` (non-callable first argument)
- **THEN** a type checker SHALL report a type error
- **AND** at runtime, a `TypeError` SHALL be raised

### Requirement: signal() auto-key shall use caller source location

When the `key` parameter is omitted, `signal()` SHALL generate a key from the caller's source location using `inspect.currentframe()` and `dis.get_instructions()`. The key format SHALL be `"{filename}:{start_line}:{start_col}"` (Python 3.11+ positions API). If the positions API is unavailable, the fallback format SHALL be `"{filename}:{lineno}"`. The key SHALL be stable across server and browser environments (same source file and line).

#### Scenario: Auto-key from source location
- **WHEN** `signal(lambda: 0)` is called at `my_component.py:10:14`
- **THEN** the generated key SHALL be `"my_component.py:10:14"`
- **AND** the same key SHALL be generated on both server and browser

#### Scenario: Same-line calls get distinct keys
- **WHEN** two `signal()` calls appear on the same source line
- **THEN** the column number SHALL disambiguate them
- **AND** each call SHALL get a distinct key

#### Scenario: Fallback when positions API unavailable
- **WHEN** `dis.get_instructions()` or `instr.positions` is not available (e.g., limited runtime)
- **THEN** the fallback key format SHALL be `"{filename}:{lineno}"`
- **AND** same-line calls SHALL share a key (user SHALL use explicit key to disambiguate)

### Requirement: Signal() direct construction shall emit UserWarning

`Signal.__init__()` SHALL emit a `UserWarning` with the message "Direct Signal() construction bypasses SSR transfer. Use signal(factory) instead." when called directly by user code. The `Signal` class SHALL remain as the return type of `signal()` and for type annotations.

An internal `Signal._create(value)` classmethod SHALL bypass the warning by using `object.__new__()` + `SignalBase.__init__()`. The `signal()` composable and other framework internals SHALL use `Signal._create()` exclusively.

#### Scenario: UserWarning on direct construction
- **WHEN** user code calls `Signal(0)` directly
- **THEN** a `UserWarning` SHALL be emitted
- **AND** the `Signal` SHALL still be created and function normally

#### Scenario: No warning from signal() composable
- **WHEN** `signal(lambda: 0)` creates a `Signal` internally
- **THEN** no `UserWarning` SHALL be emitted
- **AND** `Signal._create()` SHALL be used instead of `Signal()`

#### Scenario: Signal type annotation still works
- **WHEN** a developer writes `count: Signal[int] = signal(lambda: 0)`
- **THEN** the type annotation SHALL be valid
- **AND** `Signal` SHALL remain importable from `webcompy.signal`
