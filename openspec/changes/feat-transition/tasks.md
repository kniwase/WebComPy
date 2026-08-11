# Tasks: feat-transition

## 1. Port extension

- [ ] 1.1 Add `prefers_reduced_motion()` to `MediaQueryPort` (abstract), `BrowserMediaQueryPort` (`matchMedia("(prefers-reduced-motion: reduce)")`), and `ServerMediaQueryPort` (returns `False`), following the existing `prefers_dark` pattern; update the fake/testing port accordingly

## 2. Core element

- [ ] 2.1 Create `TransitionElement(DynamicElement)` in `packages/webcompy/src/webcompy/elements/types/_transition.py`: props parsing (`name` required non-empty string, optional `duration` in milliseconds), child generator storage, current-child tracking
- [ ] 2.2 Implement the enter sequence: mount child, apply `{name}-enter-from`, next-frame swap to `{name}-enter-active` + `{name}-enter-to`, finalization removes all classes (next-frame via double-rAF/forced-reflow behind the browser port surface; immediate in non-browser environments)
- [ ] 2.3 Implement the leave sequence: intercept child disappearance, apply `{name}-leave-from`, next-frame swap to `{name}-leave-active` + `{name}-leave-to`, keep node mounted until finalization, then run the standard removal path on the child
- [ ] 2.4 Implement duration resolution: explicit `duration` prop → computed transition/animation styles (browser) → immediate finalization with warning; end-event listeners (`transitionend`/`animationend`) with timeout backup, listeners removed on finalization
- [ ] 2.5 Implement node accounting: report the child's node count during sequences; on leave completion report zero and trigger one parent re-index; handle interruption (new child during leave finalizes the leaving node immediately) and sequential replacement (leave completes before enter starts)
- [ ] 2.6 Implement reduced-motion and environment gates: skip all sequences when `prefers_reduced_motion()` is true or outside the browser environment (mount/remove immediately)

## 3. Public API

- [ ] 3.1 Implement the `Transition` constructor accepting a props dict plus a child generator (`Transition({"name": "fade"}, generator)`); export `Transition` from `webcompy.elements` (`__init__.py` + `.pyi` if maintained)

## 4. Unit tests (`tests/test_transition.py`, browserless via TestRenderer)

- [ ] 4.1 Enter sequence: class application order (from → active+to → cleaned) with explicit `duration`; node present throughout
- [ ] 4.2 Leave sequence: node retained during leave classes, removed after duration; callback consumers destroyed; no orphaned nodes
- [ ] 4.3 Duration resolution: explicit prop honored; missing prop + no computed duration → immediate removal with warning (captured)
- [ ] 4.4 Node accounting: sibling positions stable during leave; single parent re-index after completion
- [ ] 4.5 Replacement/interruption: A→B replacement runs leave then enter with no simultaneous occupants; new child during an in-progress leave finalizes the leaving node first
- [ ] 4.6 SSR/hydration steady state: server-rendered output contains no transition classes; hydrated content does not run enter sequences
- [ ] 4.7 Reduced motion: fake port reporting reduced motion causes immediate mount/removal without classes

## 5. E2E and docs

- [ ] 5.1 Add an E2E test (Playwright, `e2e/`): a Transition-driven show/hide with real CSS — verify class sequence in the browser, delayed removal, and computed-style duration path
- [ ] 5.2 Add a docs_app demo page for `Transition` (fade/slide examples with sample CSS) and link it from the docs navigation; document the Vue-compatible class protocol, duration resolution order, and the single-child/sequential-replacement semantics

## 6. Validation

- [ ] 6.1 `uv run ruff check .` and `uv run ruff format --check .` pass
- [ ] 6.2 `uv run pyright` passes
- [ ] 6.3 `uv run python -m pytest tests/ --tb=short` passes
