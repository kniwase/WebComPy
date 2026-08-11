# Proposal: feat-teleport

## Why

Real applications need overlay-style UI — modals, toasts, dropdowns, tooltips — whose DOM nodes must render outside their logical position in the component tree to escape ancestor `overflow` clipping, stacking contexts, and `transform`-created containing blocks. WebComPy's core promise is "no JavaScript": today the only workaround is manual DOM relocation (JS-style work) or fragile `position: absolute` arrangements, as the docs_app navbar dropdown demonstrates. Every battery-included framework ships this primitive (Vue `<Teleport>`, React `createPortal`, Angular CDK portals), and because WebComPy users cannot reach for a JS ecosystem library, the framework itself must provide it.

## What Changes

- New `Teleport` element in `webcompy.elements`: `Teleport({"to": "<selector>"}, *children)` renders its children under the DOM node matched by the selector (typically `body`) while occupying a single static anchor node at its logical position in the element tree.
- SSR strategy "anchor-only": server rendering emits only the anchor placeholder at the logical position and does not render teleported content; the browser mounts children under the target after hydration. This keeps positional hydration adoption unchanged and avoids dynamic node-index accounting.
- Target resolution through the existing `DOMPort` (`query_selector`). When the target does not exist, rendering degrades to inline (children stay at the logical position) with a warning, so functionality survives misconfiguration.
- Multiple `Teleport` elements targeting the same node append in mount order. Removal of a `Teleport` removes both the teleported child nodes and the anchor.
- `to` is a static string in this change; reactive targets are deferred.
- Testing support: fake DOM in `webcompy_testing` gains the ability to resolve teleport targets.
- docs_app gains a demo page (modal + dropdown reworked onto `Teleport`) as dogfooding validation.

## Capabilities

### New Capabilities

- `teleport`: Rendering element children under a DOM target node different from their logical tree position — anchor placeholder semantics, SSR anchor-only behavior, target resolution and fallback, multi-teleport ordering, cleanup on removal, and target stability constraints.

### Modified Capabilities

(none)

## Impact

- **Code**: new `TeleportElement` under `packages/webcompy/src/webcompy/elements/types/`; public export from `webcompy.elements`; `webcompy_testing` fake DOM extension for target resolution; docs_app demo page.
- **APIs**: additive only (`Teleport`). No breaking changes.
- **Dependencies**: none (existing `DOMPort`, element machinery).
- **Downstream**: prerequisite for the planned first-party overlay components (Modal, Toast, Dropdown, Drawer) in the UI primitives work.
- **Docs**: new docs_app section demonstrating `Teleport` with a modal and a dropdown.

## Known Issues Addressed

(none)

## Non-goals

- Reactive `to` targets (re-parenting nodes when the target changes) — deferred to a later change.
- Server-side rendering of teleported content (inline-at-position or at-target variants) — the anchor-only strategy is deliberate; upgrading the SSR strategy is a future, separate change.
- Template-engine syntax (`<Teleport to="...">` inside HTML template strings) — Python API only in this change.
- A `disabled` prop (inline rendering switch) — not needed while SSR is anchor-only; may accompany a future SSR strategy upgrade.
- Teleporting into targets that live inside the app's reactive tree is supported mechanically but not recommended; the spec documents the stability constraint rather than adding guards.
