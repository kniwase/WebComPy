# Tasks: Hydration Performance Measurement

- [x] **Task 1: Add profiling infrastructure to AppConfig and WebComPyApp**

**Estimated time: ~1 hour**

### Steps

1. Add `profile: bool = False` field to `AppConfig` dataclass in `webcompy/app/_config.py`.
2. Update `WebComPyApp.__init__()` signature to accept `profile: bool = False`.
3. Add `self._profile: bool = profile` and `self._profile_data: dict[str, float] = {}`.
4. Implement `WebComPyApp._record_phase(self, name: str) -> None` that stores `time.perf_counter()` into `_profile_data` only when `_profile` is True.
5. Implement `WebComPyApp._emit_profile_summary(self) -> None` that formats `_profile_data` into the console output shown in `design.md`.
   - In Emscripten: call `browser.console.log(output)`.
   - Otherwise: call `print(output)`.
6. Add `WebComPyApp.profile_data` property returning `dict[str, float] | None`.
7. At the start of `WebComPyApp.__init__()`, call `self._record_phase("init_start")`.
8. After DI setup and component registration, call `self._record_phase("imports_done")`.
9. After `AppDocumentRoot` construction, call `self._record_phase("init_done")`.
10. Update all existing `WebComPyApp` call sites in tests to pass `profile` if needed (no changes required for backward compatibility since default is False).

### Acceptance Criteria

- `AppConfig(profile=True)` stores the value.
- `WebComPyApp(profile=True)` initializes `_profile_data` as an empty dict.
- `_record_phase` only records when `_profile` is True.
- `_emit_profile_summary` produces the expected formatted output when all keys are present.
- When `profile=False`, `profile_data` returns `None`.

---

- [x] **Task 2: Instrument render lifecycle and HTML bootstrap**

**Estimated time: ~1 hour**

### Steps

1. At the start of `WebComPyApp.run()`, call `self._record_phase("run_start")`.
2. In `AppDocumentRoot._render()` (after the recursive render completes), add `self._app._record_phase("run_done")`. Since `AppDocumentRoot` holds a reference to the app via `self._app`, call through that reference.
3. When `#webcompy-loading` is removed in `_render()`, add `self._app._record_phase("loading_removed")`. Append `self._app._emit_profile_summary()` so it runs after the DOM update.
4. In `webcompy/cli/_html.py`, update the generated `<script type="py">` template:
   - When `profile=True`, the script starts with:
     ```python
     import time
     _pyscript_ready = time.perf_counter()
     ```
   - After `app = WebComPyApp(...)`, add `app._profile_data["pyscript_ready"] = _pyscript_ready`.
   - The rest of the bootstrap (`app.run()`) remains unchanged.
5. Ensure `generate_html` receives the `profile` setting from `AppConfig`.
6. Ensure SSG does NOT inject profiling bootstrap code (the condition should be `profile and dev_mode`, or just `profile` with a server-side check).

### Acceptance Criteria

- With `profile=True`, the generated HTML `<script type="py">` contains the `_pyscript_ready` capture.
- `_profile_data` contains all 6 keys after a full browser boot: `pyscript_ready`, `init_start`, `imports_done`, `init_done`, `run_start`, `run_done`, `loading_removed`.
- `_emit_profile_summary` runs once after `loading_removed`.
- With `profile=False`, no profiling code appears in generated HTML and `_profile_data` is empty.

---

- [x] **Task 3: Add unit tests for profiling functionality**

**Estimated time: ~1 hour**

### Steps

1. Add tests in a new test file `tests/test_profiling.py`:
   - `test_profile_data_none_when_disabled`: create `WebComPyApp(profile=False)` and assert `app.profile_data is None`.
   - `test_record_phase_populates_data`: create `WebComPyApp(profile=True)`, call `_record_phase("a")`, wait a tiny amount, call `_record_phase("b")`, assert both keys exist and values are monotonically increasing.
   - `test_emit_profile_summary_format`: mock `time.perf_counter` with known values, call `_emit_profile_summary`, and assert the output string matches the expected format.
2. Add integration test in `tests/test_profiling.py` (or existing file):
   - `test_app_init_records_phases`: create `WebComPyApp(profile=True)` and assert `init_start`, `imports_done`, `init_done` are present.
3. Update `tests/e2e/` tests: no changes needed since profile is opt-in.

### Acceptance Criteria

- All new tests pass.
- Existing test suite still passes (no behavioral changes when `profile=False`).

---

## Dependencies

- None (this is the foundational change for subsequent performance work).

## Specs to Update

- `openspec/specs/app-lifecycle/spec.md` — add "The application SHALL support opt-in profiling" requirement with scenarios.
- `openspec/specs/app-config/spec.md` — add `AppConfig.profile: bool = False` to the dataclass description and scenario.
- `openspec/specs/cli/spec.md` — add profiling bootstrap to "Generated HTML shall include PyScript bootstrapping" requirement.