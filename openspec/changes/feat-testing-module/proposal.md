# Proposal: Testing Module

## Why

Currently, all test utilities (fake DOM nodes, fake port implementations, browser mock fixtures) live in `tests/conftest.py`. These utilities are imported directly by 8+ test files but are inaccessible to external projects testing their own WebComPy apps. After `feat-virtual-dom` completes, `VirtualDOMNode` + `VirtualDOMEvent` + unified render path enables rich server-side component testing. A proper testing module makes this accessible.

## What Changes

- **NEW** `webcompy/testing/` package — public API for testing WebComPy components
- **MOVED** `FakeDOMNode`, `FakeBrowserDOMPort`, `FakeBrowserHostPort`, `FakeBrowserFFIPort` from `tests/conftest.py` into `webcompy/testing/`
- **NEW** `create_browser_scope()` — pre-configured `DIScope` with browser-side fake ports
- **NEW** `create_server_scope()` — pre-configured `DIScope` with `ServerDOMPort` for virtual DOM testing
- **NEW** `create_test_app()` — minimal `WebComPyApp` factory for component rendering tests
- **NEW** `TestRenderer` / `TestRendererResult` — jsdom-like high-level API: render components, query virtual DOM trees, dispatch events, re-render
- **NEW** `"webcompy.testing"` added to `_BROWSER_ONLY_EXCLUDE` — excludes the module from browser wheels
- **MIGRATED** `tests/e2e/test_component.py`, `test_standalone.py`, `test_bundled_deps.py`, `test_static_site.py`, `test_runtime_local.py` (24 tests) — purely rendering tests, no browser interaction
- **MIGRATED** `tests/e2e/test_switch.py`, `test_reactive.py`, `test_repeat.py`, `test_keyed_repeat.py` (4/5), `test_dict_repeat.py` (4/5), `test_nested_dynamic.py`, `test_scoped_style.py` (2/7), `test_di.py` (4/5), `test_lifecycle.py` (2/3) — interactive tests now covered by `TestRenderer.render()` + `VirtualDOMEvent` dispatch + `rerender()` + virtual tree assertions

## Capabilities

### New Capabilities

- `testing-module`: `webcompy.testing` package providing `FakeDOMNode`, fake port implementations, scope helpers, and `TestRenderer` for component rendering tests. External apps can import `from webcompy.testing import TestRenderer` and write tests that render components to `VirtualDOMNode` trees, query the structure, dispatch events, and assert on the resulting virtual DOM.

## Known Issues Addressed

- **`FakeBrowserFFIPort` Protocol non-compliance** — adds missing `to_js` and `assign` methods
- **Test utilities inaccessible to external apps** — `FakeDOMNode` and fake ports become importable via `webcompy.testing`
- **E2E tests for rendering-only behavior** — migrated to unit tests; E2E retains only browser-required tests (getComputedStyle, input widget state, RouterView lifecycle)

## Non-goals

- Full jsdom-level CSS cascade or layout computation (getComputedStyle remains browser-only)
- Real browser `<input>` widget state emulation (verified in E2E with `input.fill()`)
- Navigation via `window.history.pushState` / `popstate` (tested via `MockHistoryPort` / `HistoryPort`; RouterView mount/unmount lifecycle requires E2E)
- Console error capture (`assert_no_console_errors` requires real PyScript runtime)

## Dependency

- **Requires** `feat-virtual-dom` — depends on `VirtualDOMNode`, `VirtualDOMEvent`, `ServerDOMPort.render_html()`, unified render path, and RouterLink `_on_click` fix

## Impact

- **Affected modules**: new `webcompy/testing/` package, `tests/conftest.py` (shrink), `tests/e2e/*` (shrink), `webcompy/cli/_wheel_builder.py` (1-line exclusion addition)
- **Breaking**: None for framework users. `tests/conftest.py` re-exports from `webcompy.testing` for backwards compatibility; test code can migrate gradually.
- **Testing**: ~55 E2E tests migrate to unit tests; ~11 E2E tests remain browser-required
