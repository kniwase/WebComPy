# Proposal: Client-Only Component

## Why

WebComPy has a dual-environment architecture (browser via PyScript and server via CPython), but there is no built-in mechanism for conditionally rendering content only in the browser. Developers who need browser-specific UI (interactive charts, canvas animations, real-time subscriptions) must manually check `ENVIRONMENT == "pyscript"` in component setup or use `switch()` with an environment signal. Both approaches are problematic:

1. **Manual `ENVIRONMENT` checks** are error-prone and scatter environment logic throughout application code.
2. **`switch()` with environment signals** still evaluates the browser branch's generator function during SSR/SSG, potentially triggering expensive setup (async fetches, signal creation, DI scope changes) that is immediately discarded.

A `ClientOnly` element gives developers a declarative, zero-cost abstraction: the children generator is never called on the server, and during hydration the server-rendered fallback is seamlessly replaced with actual content.

## What Changes

- **NEW** `ClientOnly` DynamicElement — renders `fallback` during SSR/SSG and `children` in the browser
- **NEW** `client_only` generator function in `packages/webcompy/src/webcompy/elements/generators.py` — factory API matching `switch`/`repeat` pattern
- **UPDATED** `packages/webcompy/src/webcompy/elements/__init__.py` — export `ClientOnly`
- **UPDATED** `packages/webcompy/src/webcompy/elements/types/__init__.py` — export `ClientOnlyElement`
- **UPDATED** Hydration handling — `ClientOnlyElement._hydrate_node()` replaces fallback DOM nodes with actual children during browser hydration

## Capabilities

### New Capabilities

- `client-only`: Built-in `ClientOnly` element that skips children generator evaluation entirely during SSR/SSG, renders fallback content on the server, and replaces fallback with actual children during browser hydration.

### Modified Capabilities

- `elements`: New `ClientOnlyElement` DynamicElement subclass alongside `SwitchElement` and `RepeatElement`
- `architecture`: Formalizes environment-conditional rendering as a framework primitive

## Known Issues Addressed

- **No built-in browser-only rendering primitive** — developers must manually guard with `ENVIRONMENT` checks or use `switch()` which evaluates both branches' generators
- **SSR resource waste** — browser-specific component setup (async fetches, signal creation) executes during SSG even though its output is discarded
- **Hydration mismatch risk** — manual `ENVIRONMENT` checks inside templates can cause server/client DOM structure mismatches that break hydration

## Non-goals

- **Server-only rendering** — `ClientOnly` is unidirectional (client-side only). A `ServerOnly` element is not in scope but could be added later.
- **Async loading states** — `ClientOnly` does not manage loading transitions or skeleton animations. The `fallback` is a static render, not a loading indicator with automatic transitions.
- **Streaming SSR** — `ClientOnly` does not support streaming the children content to the client after the initial page load. Hydration replaces fallback with actual content synchronously.
- **Component-level code splitting** — `ClientOnly` does not affect which Python code is bundled into the browser wheel. All code is always present; only rendering is conditional.
- **Changing the `ENVIRONMENT` detection mechanism** — `ClientOnly` uses the existing `ENVIRONMENT == "pyscript"` check. No new environment detection API is introduced.

## Dependency

- **Requires** `feat/async-rendering-pipeline` — `ClientOnlyElement._render()` needs the async `_render()` path to support CSR-only rendering in the browser without blocking the initial paint. The async rendering pipeline ensures that the browser can render children asynchronously after the fallback has been shown.

## Impact

- **Affected modules**: `packages/webcompy/src/webcompy/elements/types/_client_only.py` (new), `packages/webcompy/src/webcompy/elements/types/__init__.py`, `packages/webcompy/src/webcompy/elements/generators.py`, `packages/webcompy/src/webcompy/elements/__init__.py`, `packages/webcompy/src/webcompy/app/_root_component.py` (hydration)
- **Breaking**: None. `ClientOnly` is an additive feature. Existing components and elements work unchanged.
- **Testing**: Unit tests for SSR rendering (fallback only, children generator not called), browser rendering (children only, fallback not rendered), and hydration (fallback → children replacement). E2E test for full hydration flow.