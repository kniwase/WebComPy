# Tasks: Split Mode — Detached Wheel Serving for Browser Cache Optimization

**NOTE: Tasks are preliminary and will be revised based on experiment results.**

- [ ] **Task 0: Experiment with `files` + `micropip` approach**
  - Build a minimal test with 2-3 local wheels using PyScript `files` config and `micropip.install()`
  - Measure initialization time vs. bundled mode
  - Document results and decide on implementation strategy
  - Update this proposal and design based on findings

- [ ] **Task 1: Add `wheel_mode` to AppConfig** (after experiment confirms approach)
  - Add `wheel_mode: Literal["bundled", "split"] = "bundled"` to `AppConfig`
  - Add `--wheel-mode` CLI flag
  - Write unit tests

- [ ] **Task 2: Implement split wheel generation** (after experiment confirms approach)
  - Reintroduce `make_browser_webcompy_wheel()`
  - Produce per-dependency wheels via `make_wheel()`
  - Update `make_webcompy_app_package()` for app-only wheel in split mode

- [ ] **Task 3: Update HTML generation for split mode** (after experiment confirms approach)
  - Implement the validated loading strategy in `generate_html()`
  - Write unit tests

- [ ] **Task 4: Update dev server and SSG for multi-wheel serving** (after experiment confirms approach)
  - Serve multiple wheel files with appropriate cache headers
  - Update SSG output for multiple wheel files
  - Write E2E tests