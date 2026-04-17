## Why

The codebase contains several consistent typos in internal APIs: `_get_evnet` (should be `_get_event`), `__webcompy_componet_definition__` (should be `__webcompy_component_definition__`), `componet_generator` (should be `component_generator`), and `__conponents` (should be `__components`). These typos are used throughout the codebase and make the code harder to read and maintain.

## What Changes

- Rename `_get_evnet` to `_get_event` across all reactive modules (20 occurrences)
- Rename `__webcompy_componet_definition__` to `__webcompy_component_definition__` (2 occurrences)
- Rename `componet_generator` parameter to `component_generator` (1 occurrence)
- Rename `__conponents` to `__components` (5 occurrences)

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None — these are internal implementation details with no observable behavior change.

## Impact

- `webcompy/reactive/_base.py` — `_get_evnet` method definition
- `webcompy/reactive/_computed.py`, `_list.py`, `_dict.py` — `_get_evnet` usage
- `webcompy/router/_change_event_handler.py` — `_get_evnet` usage
- `webcompy/aio/_aio.py` — `_get_evnet` usage
- `webcompy/components/_generator.py` — `__conponents`, `componet_generator`, `__webcompy_componet_definition__`
- `webcompy/components/_component.py` — `__webcompy_componet_definition__` usage
- All `.pyi` stub files referencing these names
- Test files referencing these names

## Known Issues Addressed

- `_get_evnet` (typo for `_get_event`) is consistently used throughout the codebase
- `__webcompy_componet_definition__` (typo for "component") is consistently used

## Non-goals

- Refactoring the underlying patterns (e.g., replacing the decorator pattern, adding DI)
- Changing any external or public API behavior
- Fixing any non-typo code quality issues