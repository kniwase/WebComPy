## Why

The merged `feat-signal-value-transfer` relies on `__signal_members__` populated via `self.X = Signal()`, which is impossible in the current function-style component API (user setup functions receive `context`, not `self`). The signal collection path collects zero signals from any user component in any real application — the feature is effectively dead code.

Additionally, the current restoration mechanism (`_restore_signals()` in `_render()`) is fragile: restored values can be overwritten by lifecycle hooks that run after restoration.

This change introduces a `signal()` composable with a factory-skip transfer mechanism, modeled after Nuxt's `useState` and the existing `use_async_result` pattern. On the server, the factory runs to produce the initial value. On the browser during hydration, the factory is skipped and the value is restored from the hydration payload — all during setup, before lifecycle hooks run.

This change depends on `fix-async-component-active-context` (Phase 1) to ensure `signal()` works inside async component setup functions.

## What Changes

- Introduce `signal(factory: Callable[[], T]) -> Signal[T]` composable with `@overload` for `(key: str, factory: Callable[[], T])` variant — the sole recommended way to create transferable signals
- Factory-skip mechanism: on the server, the factory runs and produces the initial value; on the browser during hydration, `signal()` checks `HYDRATION_SIGNAL_DATA_KEY` and skips the factory if a value is found, creating the `Signal` with the restored value directly
- Deprecate `Signal()` direct construction with `UserWarning` (class stays as return type and internal implementation)
- Add `Signal._create()` classmethod as internal bypass (thread-safe, no warning)
- Add `_transferable_signals: dict[str, SignalBase]` to `Context` for registration during setup
- In `Component.__setup()`, merge `context._transferable_signals` into `self.__signal_members__` after the setup function returns (enabling existing `collect_transfer_data()` to work unchanged)
- Remove `_restore_signals()` from `Component._render()` (restoration now happens during setup via factory-skip)
- Auto-key generation via `inspect` + `dis` (file:line:column) with `file:line` fallback

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `signal-value-transfer`: Restoration mechanism changes from `_restore_signals()` in `_render()` to factory-skip during setup; scenarios rewritten for `signal()` composable syntax; `HYDRATION_SIGNAL_DATA_KEY` SHALL be provided before component creation
- `composables`: Add `signal()` composable requirement — factory-skip transfer, `@overload` typing, graceful degradation outside component context
- `hydration-data-transfer`: `app.run()` SHALL provide `HYDRATION_SIGNAL_DATA_KEY` in the root DI scope alongside `HYDRATION_DATA_KEY`

## Impact

- `packages/webcompy/src/webcompy/signal/_composable.py` (new) — `signal()` function with `@overload` typing and auto-key generation
- `packages/webcompy/src/webcompy/signal/__init__.py` — export `signal`
- `packages/webcompy/src/webcompy/__init__.py` — re-export `signal`
- `packages/webcompy/src/webcompy/signal/_signal.py` — `Signal.__init__` gains `UserWarning`; add `Signal._create()` classmethod
- `packages/webcompy/src/webcompy/components/_libs.py` — `Context` gains `_transferable_signals` dict
- `packages/webcompy/src/webcompy/components/_component.py` — `__setup()` merges `_transferable_signals`; `_render()` drops `_restore_signals()`
- `packages/webcompy/src/webcompy/di/_keys.py` — verify `HYDRATION_SIGNAL_DATA_KEY` exists and is provided in `app.run()`
- `packages/webcompy/src/webcompy/app/_render_context.py` or `_app.py` — provide `HYDRATION_SIGNAL_DATA_KEY` before component creation

## Known Issues Addressed

- `__signal_members__` is never populated for user components in function-style API → `signal()` composable provides the registration path via `Context._transferable_signals`

## Non-goals

- Adding `ReactiveList` / `ReactiveDict` transfer support (separate investigation: `investigate-reactive-collections`)
- Deprecating the `Signal` class entirely (separate change: `refactor-signal-api-unification`)
- Module-level signal transfer (separate future change)
- Changing the `collect_transfer_data()` collection mechanism (unchanged — still walks `__signal_members__`)
- Changing the payload serialization format (unchanged — version 2 with `signals` section)
