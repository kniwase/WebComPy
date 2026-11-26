# Proposal: fix-element-signal-ownership

## Why

`ElementAbstract` inherits `SignalReceivable.__setattr__`, which automatically claims any `SignalBase` assigned to an element attribute as a framework-owned signal member and destroys its producer edges in `consumer_destroy()` during `_remove_element()` or `_detach_from_node()`. As a result, elements storing caller-supplied signals (such as `RepeatElement`, `TextElement`, `RawHTMLElement`, `SwitchElement`, `TypedRouterLink`, and `MarkdownForElement`) permanently sever caller-owned `Computed` and reactive collection signals when conditionally unmounted, patched across switch branches, or refreshed.

## What Changes

- Opt `ElementAbstract` and all virtual DOM element subclasses out of implicit `SignalReceivable.__setattr__` attribute claiming so borrowed caller signals are never destroyed on element unmount, switch-patch detachment, or refresh.
- Introduce single-owner claiming for framework-created `_OwnedComputed` instances so interpolated attributes, expressions, radio `:bind` bindings, component-tag props, and dynamic control-flow nodes are destroyed exactly when their true owning node tears down (and cannot be stolen or prematurely destroyed by inner child elements).
- Transfer pre-claimed template-root signal ownership cleanly in `Component._init_component` (`generator is None` path used by `AppDocumentRoot`), register internal framework `Computed`s explicitly on `RouterView`, `TypedRouterLink`, and `_DictValueRow`, convert remaining internal `Computed` sites in template binding, `MultiLineTextElement`, and radio `:bind` to `_OwnedComputed`, and guard `MarkdownForElement` against duplicate allocation on reparenting.
- Update `elements` and `reactive` OpenSpec specifications to document the ownership boundary between caller-supplied and framework-owned signals.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `elements`: specify that element teardown and detachment destroy only framework-owned signals while preserving caller-owned reactive inputs, props, and conditions.
- `reactive`: clarify that `SignalReceivable.__setattr__` automatic tracking applies to non-element subclasses, while virtual DOM elements opt out in favor of explicit framework ownership registration.

## Impact

- `packages/webcompy/src/webcompy/signal/_computed.py`
- `packages/webcompy/src/webcompy/elements/types/_abstract.py`, `_element.py`, `_text.py`, `_repeat.py`, `_switch.py`
- `packages/webcompy/src/webcompy/elements/_bind.py`
- `packages/webcompy/src/webcompy/components/_component.py`
- `packages/webcompy/src/webcompy/template/_binder.py`, `_markdown_for.py`
- `packages/webcompy/src/webcompy/router/_link.py`, `_view.py`
- Unit tests (`tests/test_element_signal_ownership.py`) and browser-tier tests (`tests/browser/`)

## Known Issues Addressed

- Fixes premature `consumer_destroy()` destruction of caller-owned `Computed` and reactive signals in `RepeatElement`, `TextElement`, `RawHTMLElement`, `SwitchElement`, `TypedRouterLink`, and `MarkdownForElement` on conditional unmount, `SwitchElement` patching, and `RouterLink._refresh()`.
- Prevents accidental registration of `Component._observed_props` in `__signal_members__`.

## Non-goals

- Automatic disposal of user-created `use_computed()` / `Computed()` signals allocated inside component setup functions when a component unmounts (left outside element ownership scope).
- Simplifying or modifying the `docs_app/static/_demos/migration_users/app.py` workaround or other demo applications.
