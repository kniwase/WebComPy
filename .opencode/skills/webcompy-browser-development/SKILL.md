---
name: webcompy-browser-development
description: Develop WebComPy browser-side runtime code (components, elements, reactive signals, router, ports). Use when modifying packages/webcompy browser runtime internals.
---

You are working on browser-side WebComPy runtime code that runs via PyScript/Emscripten.

## Core Responsibilities

- Component framework internals (Component base class, ComponentGenerator, define_component, lifecycle hooks, ComponentContext)
- Reactive system internals (signal propagation, computed evaluation, list reconciliation)
- Virtual DOM / element system (DOM creation, patching, hydration)
- Client-side routing (history/hash modes, path params, navigation)
- Browser API abstraction layer
- Application bootstrapping (WebComPyApp, AppConfig) and DI scope management

## Key Constraints

- No standard library modules are available at runtime in the browser
- Browser APIs are accessed through the `js` module
- Use `platform.system() == "Emscripten"` to detect browser environment

## Runtime Context Detection

`packages/webcompy/src/webcompy/` and `packages/webcompy/src/webcompy/_browser/` are browser-accessible. Code entering the browser checks `platform.system() == "Emscripten"`. Imports of `js` indicate browser code paths; `uvicorn`/`starlette`/`aiofiles` imports indicate server-only code (must not appear in browser modules).

## OpenSpec References

Before modifying runtime code, read the relevant specs to ensure compliance:

- `openspec/specs/reactive/spec.md` — Signal equality, notification, lazy evaluation
- `openspec/specs/effect/spec.md` — Side-effect tracking and cleanup
- `openspec/specs/elements/spec.md` — DOM element creation, reactive updates, conditional/list rendering
- `openspec/specs/list-reconciliation/spec.md` — Key-based DOM reconciliation for lists
- `openspec/specs/nested-dynamic-element/spec.md` — repeat/switch nesting at arbitrary depth
- `openspec/specs/router/spec.md` — Client-side routing modes and path params
- `openspec/specs/router-hooks/spec.md` — before_route_change, after_route_change, on_route_error
- `openspec/specs/browser-api/spec.md` — Browser environment detection
- `openspec/specs/di-scope/spec.md` — DI resolution boundary and lifecycle
- `openspec/specs/di-injection/spec.md` — provide/inject pattern
- `openspec/specs/app-lifecycle/spec.md` — App start/run/shutdown

## Patterns

- Reactive contracts: `old is new or old == new` for same-value suppression
- Computed is lazily evaluated — only recomputes when read after dirty
- Event handlers must be created via `create_proxy()` and `destroy()`ed on removal
- Component destruction must dispose its DI child scope
- `_hydrate_node()` adopts existing prerendered nodes, never creates new ones

## Related Skills

- `webcompy-server-development` — server-side runtime (CLI, dev server, SSG) shares dual-environment code (`webcompy.app`)
- `webcompy-component-development` — building application UI components using the public component API (not framework internals)
- `webcompy-inspect` — verifying browser runtime behavior in a real browser
- `webcompy-review` — spec-driven code review for PRs
