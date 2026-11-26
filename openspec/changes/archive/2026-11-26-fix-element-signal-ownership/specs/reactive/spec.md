# Spec Delta

## MODIFIED Requirements

### Requirement: SignalReceivable shall track signal members by attribute name

`SignalReceivable.__signal_members__` SHALL be a `dict[str, SignalBase]` mapping attribute name to the Signal instance owned by that object. For non-element `SignalReceivable` subclasses, `__setattr__` SHALL call `__set_signal_member__(name, value)` when the value is a `SignalBase` instance, passing the attribute name. Virtual DOM elements (`ElementAbstract` and its subclasses) SHALL opt out of implicit attribute claiming in `__setattr__` and register only framework-owned signals explicitly via `__set_signal_member__`. `computed_property` SHALL register its `Computed` instances by the method name on any `SignalReceivable`, consistent with attribute-name keying.

#### Scenario: Signal assigned to self is tracked by name
- **WHEN** a non-element `SignalReceivable` instance executes `self.count = Signal(0)`
- **THEN** `self.__signal_members__["count"]` SHALL reference the `Signal` instance

#### Scenario: Computed property is tracked by name
- **WHEN** a `SignalReceivable` instance has a `@computed_property` method named `doubled`
- **AND** the property is accessed (triggering Computed creation)
- **THEN** `self.__signal_members__["doubled"]` SHALL reference the `Computed` instance

#### Scenario: Reassigning a Signal attribute updates the registry
- **WHEN** a non-element `SignalReceivable` instance executes `self.count = Signal(0)` then `self.count = Signal(5)`
- **THEN** `self.__signal_members__["count"]` SHALL reference the second `Signal(5)` instance
- **AND** the first `Signal(0)` instance SHALL no longer be in the registry

#### Scenario: Non-Signal attributes are not tracked
- **WHEN** a `SignalReceivable` instance executes `self.name = "Alice"` (a plain string)
- **THEN** `self.__signal_members__` SHALL NOT contain `"name"`

#### Scenario: Virtual DOM elements opt out of implicit attribute claiming
- **WHEN** an `ElementAbstract` subclass assigns a caller-supplied `SignalBase` to an instance attribute (`self._sequence`, `self._text`, `self._to`, etc.)
- **THEN** `self.__signal_members__` SHALL NOT register that borrowed signal unless explicitly claimed as framework-owned
