# Design: feat-transition

## Context

WebComPy removes DOM nodes immediately when conditional content disappears: reconciliation deletes unmatched children via `_remove_element(recursive=True, remove_node=True)` (`elements/types/_dynamic.py:228-232`), and there is no hook to delay removal. Exit animations are therefore impossible, and enter animations have no sanctioned timing point. The framework's "no JavaScript" promise rules out JS animation libraries; the viable model is Vue's CSS-class protocol, where the framework owns class timing and delayed removal and users write plain CSS.

Grounded facts (verified in codebase):

- **Wrapper-with-generator precedent**: `ClientOnlyElement(DynamicElement)` takes a `children: Callable[[], ElementChildren]` generator and swaps generated subtrees (`elements/types/_client_only.py`). `Transition` follows the same shape with a generator returning an element or `None`.
- **Node-count / re-index machinery**: parents compute child `_node_idx` from cumulative `_node_count` and call `_re_index_children` (`elements/types/_dynamic.py:81-91`); a transitioning child can therefore keep reporting its node while leaving and trigger one re-index when removal completes.
- **Media query port exists**: `MediaQueryPort.prefers_dark()` (`ports/_media_query.py`) with browser `matchMedia` implementation and a server default (`False`) — the pattern to extend for `prefers-reduced-motion`.
- **Computed styles reachable in browser**: `getComputedStyle` is declared on the browser window surface (`ports/_browser/_raw.pyi:65`); class manipulation is available through the `DOMNode` protocol's attribute access (`classList`).
- **SSR renders element trees without browser APIs**: server rendering must emit the steady state; transition behavior is browser-only by construction.

## Goals / Non-Goals

**Goals:**

- `Transition({"name": "<prefix>"}, child_generator)` element, single conditional child, Vue-compatible six-class protocol (`{name}-enter-from/-enter-active/-enter-to`, `{name}-leave-from/-leave-active/-leave-to`).
- Delayed DOM removal for leave transitions with duration resolution (explicit prop → computed styles → immediate + warning) and timeout backup for end-event listeners.
- Correct node-count accounting: the leaving node keeps occupying its slot; the parent re-indexes exactly once when removal completes.
- SSR/hydration render the steady state with no transition classes; no `appear` animation.
- Honor `prefers-reduced-motion` by skipping transitions.

**Non-Goals:**

- List/move transitions (TransitionGroup-equivalent), JS hooks, `appear` animations, reactive `name` (see proposal Non-goals).

## Decisions

### D1: Vue-compatible six-class protocol, CSS-only

The class sequence mirrors Vue 3's `<Transition>` exactly, so existing CSS snippets and community knowledge transfer unchanged. The framework never animates itself: it applies and removes classes at the correct frames and delays removal; all visual behavior comes from user CSS keyed off those classes. Alternative (Svelte-style per-element directives with JS-driven frames) rejected: it requires a JS animation loop, contradicting the CSS-only constraint and adding scheduler complexity.

### D2: Wrapper element with a child generator (not an element attribute)

`Transition({"name": ...}, generator)` wraps a generator that returns the current child element or `None`. Rationale: the wrapper owns the full enter/leave lifecycle of "its" child, including intercepting removal, without touching the generic reconciliation path used by unrelated elements. An attribute form (`:transition` on any element) would require intercepting removal inside `switch`/`repeat` reconciliation for arbitrary elements — a much larger surface interacting with list reconciliation invariants. The attribute form may be revisited once the wrapper semantics are proven. This also matches the `ClientOnly` API precedent and keeps v1 template-engine changes out of scope.

The wrapper SHALL wrap the generator in a `Computed` (owned as a signal member) so Signal reads inside the generator are tracked automatically. A dependency change re-evaluates the generator and drives the lifecycle; the subscription is registered as a callback consumer and destroyed with the element.

### D3: Single child only

The generator yields at most one element (or `None`). Cross-fade between two different children is out of scope for v1: when the generator's result changes between two non-`None` elements, the old child leaves and the new child enters sequentially (leave completes, then enter starts) — specified behavior, no overlap. Rationale: overlapping replacement requires managing two occupying nodes and their indices simultaneously; sequential swap keeps node accounting trivial and covers the dominant use case (show/hide).

The child SHALL be a single real-DOM node: an `ElementBase` instance (including `Component` roots). `DynamicElement` children (`Fragment`, `Teleport`, `switch`, `repeat`, `Suspense`, ...), text nodes, and other shapes are rejected with a framework validation error (`WebComPyException`), because the class protocol targets one concrete DOM node and multi-node/anchor shapes have no defined class target. When the generator result changes between two elements with the same tag name, the node is patched in place without a sequence (mirroring `_patch_children` matching); only a shape change (different tag) triggers the sequential leave-then-enter replacement.

### D4: Delayed removal via intercepted leave, one re-index at completion

When the generator switches to `None`, the element enters the leave sequence instead of removing the node: apply `-leave-from`, on the next frame swap to `-leave-active` + `-leave-to`, then wait for the end event or timeout, then run the standard `_remove_element` path on the child. During the leave, `_node_count` still reports the child's node so sibling indices stay valid; when removal completes, the Transition reports zero and the parent re-indexes once. If a new child appears while a leave is in progress, the leaving node is finalized immediately (classes cleaned, node removed) before the enter sequence starts — no overlapping occupants. When the Transition element itself is removed from the tree while a child is present, the child is removed immediately without a leave sequence (the spec's "Removing the Transition itself" scenario governs; this supersedes earlier draft wording that suggested leaving).

### D5: Duration resolution chain with mandatory timeout

End events (`transitionend`/`animationend`) do not fire when no CSS transition/animation applies, so waiting on them alone can strand nodes forever. Resolution order: (1) explicit `duration` prop in milliseconds (a non-negative number; invalid values raise a framework validation error); (2) the longest duration parsed from the node's computed `transition`/`animation` styles (browser only); (3) when neither yields a positive duration, remove immediately and log a warning. An explicit duration of `0` finishes immediately without a warning; the warning is reserved for the style-fallback path where no applicable transition/animation exists. Whichever duration is used, a timeout SHALL finalize the leave/enter even if end events never arrive or fire late. Style-resolved sequences finalize early only after every counted layer (duration plus delay positive) delivers an end event for the node; animation layers whose `animation-iteration-count` is `infinite` are excluded from the count because their end events never arrive, though their durations still contribute to the resolved timeout; an explicit `duration` prop finalizes on the first end event. End events are only honored when they target the transitioning node (descendant-bubbled events do not finalize). Listeners are removed on finalization to avoid leaks (event-handler leak invariant).

### D6: SSR steady state, no appear

Server rendering, static generation, hydration adoption, and the first browser render all render the child (if present) without transition classes; the enter sequence runs only for children created by client-side state changes after the initial render. Rationale: animating on every page load/hydration is rarely desired and complicates hydration adoption; Vue also gates this behind an opt-in `appear` prop, which stays a future option.

### D7: Reduced motion via MediaQueryPort extension

`MediaQueryPort` gains `prefers_reduced_motion()` as an abstract method (browser: `matchMedia("(prefers-reduced-motion: reduce)")`; server: `False`, same pattern as `prefers_dark`). The abstract extension is accepted while the framework is in development; the browser/server/testing implementations are updated together. When true, `Transition` skips class sequences entirely: enter mounts immediately, leave removes immediately. The preference is re-evaluated at each sequence start (no runtime listener for mid-sequence changes).

### D9: Dedicated TransitionPort for frame, timer, and computed-style access

The timing and CSSOM needs of `Transition` (next-frame scheduling, real-time timeouts with cancellation, computed-style reads) are a distinct browser API surface. The `port-abstraction` scope rules reject folding these heterogeneous responsibilities into `HostPort` or `DOMPort`, so a dedicated `TransitionPort` is introduced with: `enabled` (browser true, server false), `schedule_next_frame(callback) -> cancel` (browser: double `requestAnimationFrame` so the `-from` state is painted before the swap; non-browser: no-op cancel), `schedule_timeout(callback, delay_ms) -> cancel` (browser: `setTimeout`/`clearTimeout`), and `get_computed_style(node)` returning a read-only style view (`get_property_value(name)`; browser: `window.getComputedStyle`). A testing fake provides a logical frame queue and a virtual clock (`flush_frame()`, `advance_time(ms)`) so unit tests exercise the full class protocol without real time. The element never touches raw browser APIs directly.

### D8: Next-frame timing

The from→active/to class swap must happen after the browser has committed the initial style so the transition actually runs. The implementation uses the browser's next-frame mechanism (double `requestAnimationFrame` or forced reflow fallback) behind the DOM/browser port surface; in non-browser environments the swap is immediate (no animation occurs there anyway).

## Risks / Trade-offs

- **Sequential swap on replacement** (D3): replacing one visible child with another shows leave-then-enter rather than a cross-fade. Accepted for v1 simplicity; documented.
- **Computed-style parsing fragility** (D5): shorthand parsing of `transition`/`animation` values has edge cases (`inherit`, multiple layers). Mitigated by the explicit `duration` prop as the reliable path and the immediate-removal fallback; E2E covers the common cases.
- **Warning noise**: a transition without an explicit `duration` and without CSS on the active classes finishes immediately and warns. This is specified behavior for the style-fallback path; the docs demo always ships CSS.
- **Node-cache invariants**: the leaving node keeps a live `_node_cache` while logically "removed" from the generator's perspective; the implementation SHALL keep strict is-None discipline (clear cache only at actual removal) per the async-rendering invariants.
- **Nested transitions inside Teleport/Suspense**: composition follows ordinary element-tree rules (each Transition manages its own child); no special coupling, but E2E covers the Teleport+Transition combination since the UI primitives depend on it.
