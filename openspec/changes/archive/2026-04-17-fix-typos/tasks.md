## 1. Reactive System — `_get_evnet` → `_get_event`

- [x] 1.1 Rename `_get_evnet` to `_get_event` in `webcompy/reactive/_base.py` (definition and self-usage)
- [x] 1.2 Update all `_get_evnet` references in `webcompy/reactive/_computed.py`
- [x] 1.3 Update all `_get_evnet` references in `webcompy/reactive/_list.py`
- [x] 1.4 Update all `_get_evnet` references in `webcompy/reactive/_dict.py`
- [x] 1.5 Update all `_get_evnet` references in `webcompy/router/_change_event_handler.py`
- [x] 1.6 Update all `_get_evnet` references in `webcompy/aio/_aio.py`

## 2. Component System — typo renames

- [x] 2.1 Rename `__conponents` to `__components` and `componet_generator` to `component_generator` in `webcompy/components/_generator.py`
- [x] 2.2 Rename `__webcompy_componet_definition__` to `__webcompy_component_definition__` in `webcompy/components/_generator.py` and `webcompy/components/_component.py`

## 3. Stub and Test Files

- [x] 3.1 Update `.pyi` stub files that reference any renamed identifiers
- [x] 3.2 Update test files that reference any renamed identifiers

## 4. Verification

- [x] 4.1 Run `uv run ruff check .` and `uv run ruff format .` to verify lint/format
- [x] 4.2 Run `uv run pyright` to verify type checking passes
- [x] 4.3 Run `uv run python -m pytest tests/ --tb=short` to verify all tests pass