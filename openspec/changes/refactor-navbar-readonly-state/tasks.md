## 1. Refactor Navbar state management

- [x] 1.1 Replace the per-menu `_menu_positions` lazy dict with a single canonical `positions, update_positions = use_readonly_signal({})` snapshot (`dict[int, tuple[float, float]]`) in `docs_app/components/navigation.py`
- [x] 1.2 Add `_measure_open_menus()` returning the snapshot dict (existing re-measure logic moved from the void-returning helper); keep the `dom` guard for browser-only measurement
- [x] 1.3 Replace the manual scroll/resize listeners and their `HOST_PORT_KEY`/`DOM_PORT_KEY` wiring with `use_document_event("scroll", {}, transform=_measure)` and `use_window_event("resize", {}, transform=_measure)`, where `_measure` writes the canonical snapshot via `update_positions` and returns it
- [x] 1.4 Update `_toggle` to measure immediately after opening and write through `update_positions`
- [x] 1.5 Keep the click-outside listener manual (`add_document_event_listener` + `on_before_destroy`), registered before the event composable calls so their chained cleanup is not overwritten
- [x] 1.6 Update the dropdown style `use_computed` read sites to `positions.value.get(idx, (0.0, 0.0))`; remove the now-unused per-menu position accessors

## 2. Verification

- [x] 2.1 Run `uv run python -m webcompy generate` on docs_app and confirm the SSG output is unchanged in structure
- [x] 2.2 Run `uv run ruff check .` / `uv run ruff format --check` / `uv run pyright`
- [x] 2.3 Run `scripts/run-e2e-tests.sh docs-home` (dropdown open/close, navigation, mobile dropdown) and confirm all pass
- [x] 2.4 Manually verify with `webcompy inspect` (or browser) that dropdowns re-position on scroll/resize and that clicking outside closes them
