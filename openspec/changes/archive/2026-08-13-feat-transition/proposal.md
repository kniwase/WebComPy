# Proposal: feat-transition

## Why

WebComPy can show and hide elements, but it cannot animate them: conditional removal deletes DOM nodes immediately, so exit animations are impossible and enter animations have no sanctioned hook. Every battery-included framework ships CSS-driven transition support (Vue `<Transition>`, Svelte `transition:`, Angular animations), and since WebComPy users cannot reach for JS animation libraries without breaking the "no JavaScript" promise, the framework must provide the lifecycle itself. The minimal high-value capability is a CSS-class-driven enter/leave protocol for single conditional elements — the same model as Vue's `<Transition>` — where the framework owns class timing and delayed DOM removal while users supply plain CSS.

## What Changes

- New `Transition` element in `webcompy.elements`: `Transition({"name": "<prefix>"}, child_generator)` wraps a single reactive child (a generator returning an element or `None`) and drives a Vue-compatible six-class CSS protocol around its appearance and disappearance:
  - enter: `{name}-enter-from` → (next frame) `{name}-enter-active` + `{name}-enter-to` → (transition/animation end) classes removed.
  - leave: removal intercepted; `{name}-leave-from` → (next frame) `{name}-leave-active` + `{name}-leave-to` → (transition/animation end) node actually removed.
- Delayed removal: while a leave transition runs, the outgoing node stays mounted; the element reports its node count accordingly and the parent re-indexes once when removal completes.
- Duration resolution: explicit `duration` prop (milliseconds) takes precedence; otherwise durations are read from the node's computed styles (`transition`/`animation`); when neither yields a positive duration the node is removed immediately with a warning. A timeout always backs up the `transitionend`/`animationend` listeners.
- SSR renders the current state without transition classes; no initial-render ("appear") animation in this change.
- `prefers-reduced-motion` is honored: transitions are skipped for users who request reduced motion. Detection is an additive `prefers_reduced_motion()` method on the existing `MediaQueryPort` (browser media query; server returns false), following the established `prefers_dark` pattern.
- Scope is single conditional elements; list/repeated transitions (TransitionGroup-equivalent) are deferred.

## Capabilities

### New Capabilities

- `transition`: CSS-class-driven enter/leave transition lifecycle for a single conditional child — Vue-compatible class protocol, delayed removal with duration resolution and timeout fallback, node-count/re-index behavior, SSR steady-state rendering, and reduced-motion support.

### Modified Capabilities

(none)

## Impact

- **Code**: new `TransitionElement` under `packages/webcompy/src/webcompy/elements/types/`; public export from `webcompy.elements`; `prefers_reduced_motion()` on `MediaQueryPort` and its browser/server/testing implementations; a new dedicated `TransitionPort` (frame/timer/computed-style abstraction) with browser, server, and testing implementations, registered in both render contexts and the testing renderer; unit tests under `tests/`; E2E tests under `e2e/`; docs_app demo page.
- **APIs**: additive element API (`Transition`). `MediaQueryPort` gains an abstract `prefers_reduced_motion()` method; because the framework is still in development, existing third-party `MediaQueryPort` subclasses are not part of the compatibility surface and the abstract extension is accepted.
- **Dependencies**: none (existing element machinery and DI port provisioning).
- **Downstream**: used by the planned first-party UI primitives (overlay open/close, disclosure expand/collapse) for polish.
- **Docs**: new docs_app demo page demonstrating enter/leave transitions with sample CSS, linked from the docs navigation.

## Known Issues Addressed

(none)

## Non-goals

- List transitions / move animations (TransitionGroup-equivalent, FLIP) — separate future change.
- JavaScript animation hooks or an animation engine — CSS-class protocol only.
- `appear` (initial-render) animations — SSR and hydration render the steady state.
- Reactive `name` changes mid-transition and transition cancellation APIs beyond what removal/replacement naturally triggers.
- Multiple simultaneous children (the child generator yields at most one element).
