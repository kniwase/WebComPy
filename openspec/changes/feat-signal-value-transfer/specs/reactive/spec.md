## ADDED Requirements

### Requirement: SignalReceivable shall track signal members by attribute name

`SignalReceivable.__signal_members__` SHALL be a `dict[str, SignalBase]` mapping attribute name to the Signal instance assigned to that attribute. `__setattr__` SHALL call `__set_signal_member__(name, value)` when the value is a `SignalBase` instance, passing the attribute name. `computed_property` SHALL register its `Computed` instances by the method name, consistent with the attribute-name keying.

#### Scenario: Signal assigned to self is tracked by name
- **WHEN** a component executes `self.count = Reactive(0)`
- **THEN** `self.__signal_members__["count"]` SHALL reference the `Reactive` instance

#### Scenario: Computed property is tracked by name
- **WHEN** a component has a `@computed_property` method named `doubled`
- **AND** the property is accessed (triggering Computed creation)
- **THEN** `self.__signal_members__["doubled"]` SHALL reference the `Computed` instance

#### Scenario: Reassigning a Signal attribute updates the registry
- **WHEN** a component executes `self.count = Reactive(0)` then `self.count = Reactive(5)`
- **THEN** `self.__signal_members__["count"]` SHALL reference the second `Reactive(5)` instance
- **AND** the first `Reactive(0)` instance SHALL no longer be in the registry

#### Scenario: Non-Signal attributes are not tracked
- **WHEN** a component executes `self.name = "Alice"` (a plain string)
- **THEN** `self.__signal_members__` SHALL NOT contain `"name"`
