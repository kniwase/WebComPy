# Tasks: feat-transition

## 1. Port extension

- [x] 1.1 Add `prefers_reduced_motion()` to `MediaQueryPort` (abstract), `BrowserMediaQueryPort` (`matchMedia("(prefers-reduced-motion: reduce)")`), and `ServerMediaQueryPort` (returns `False`), following the existing `prefers_dark` pattern; update the fake/testing port accordingly
- [x] 1.2 Add a dedicated `TransitionPort` ABC in `webcompy.ports` with `enabled`, `schedule_next_frame(callback) -> cancel`, `schedule_timeout(callback, delay_ms) -> cancel`, and `get_computed_style(node)` (read-only style view via `get_property_value`); add `TRANSITION_PORT_KEY` and export both from `webcompy.ports`
- [x] 1.3 Implement `BrowserTransitionPort` (double `requestAnimationFrame`, `setTimeout`/`clearTimeout`, `window.getComputedStyle`), `ServerTransitionPort` (`enabled=False`, empty style, no-op cancels), and a `FakeTransitionPort` with a logical frame queue and virtual clock (`flush_frame()`, `advance_time(ms)`) plus a fake media-query port; register the ports in `BrowserRenderContext`/`ServerRenderContext`, `TestRenderer`, and the `tests/conftest.py` fixtures; expose `transition_port`/`media_query_port` on `TestRendererResult`; update `tests/test_markdown_di.py` browser-port stub list

## 2. Core element

- [x] 2.1 Create `TransitionElement(DynamicElement)` in `packages/webcompy/src/webcompy/elements/types/_transition.py`: props parsing (`name` required non-empty string, `duration` optional non-negative number of milliseconds), child generator wrapped in an owned `Computed` with a callback consumer subscription, current-child tracking, and child-shape validation (single `ElementBase` / `Component` root; `DynamicElement`, text, and other shapes raise `WebComPyException`)
- [x] 2.2 Implement the enter sequence: mount child, apply `{name}-enter-from`, next-frame swap to `{name}-enter-active` + `{name}-enter-to`, finalization removes all classes (next-frame via double-rAF/forced-reflow behind the browser port surface; immediate in non-browser environments)
- [x] 2.3 Implement the leave sequence: intercept child disappearance, apply `{name}-leave-from`, next-frame swap to `{name}-leave-active` + `{name}-leave-to`, keep node mounted until finalization, then run the standard removal path on the child
- [x] 2.4 Implement duration resolution: explicit `duration` prop → computed transition/animation styles (browser) → immediate finalization with warning (no warning for explicit zero); end-event listeners (`transitionend`/`animationend`, target-checked) with timeout backup, listeners removed on finalization
- [x] 2.5 Implement node accounting: report the child's node count during sequences; on leave completion report zero and trigger one parent re-index; handle interruption (new child during leave finalizes the leaving node immediately) and sequential replacement (leave completes before enter starts); wrapper removal cancels sequences and removes the child immediately
- [x] 2.6 Implement reduced-motion and environment gates: skip all sequences when `prefers_reduced_motion()` is true or the transition port is disabled (mount/remove immediately)

## 3. Public API

- [x] 3.1 Implement the `Transition` constructor accepting a props dict plus a child generator (`Transition({"name": "fade"}, generator)`); export `Transition` from `webcompy.elements` (`__init__.py` + `.pyi` if maintained)

## 4. Unit tests (`tests/test_transition.py`, browserless via TestRenderer)

- [x] 4.1 Enter sequence: class application order (from → active+to → cleaned) with explicit `duration`; node present throughout
- [x] 4.2 Leave sequence: node retained during leave classes, removed after duration; callback consumers destroyed; no orphaned nodes
- [x] 4.3 Duration resolution: explicit prop honored; missing prop + no computed duration → immediate removal with warning (captured)
- [x] 4.4 Node accounting: sibling positions stable during leave; single parent re-index after completion
- [x] 4.5 Replacement/interruption: A→B replacement runs leave then enter with no simultaneous occupants; new child during an in-progress leave finalizes the leaving node first
- [x] 4.6 SSR/hydration steady state: server-rendered output contains no transition classes; hydrated content does not run enter sequences
- [x] 4.7 Reduced motion: fake port reporting reduced motion causes immediate mount/removal without classes

## 5. E2E and docs

- [x] 5.1 Add an E2E test (Playwright, `e2e/`): a Transition-driven show/hide with real CSS — verify class sequence in the browser, delayed removal, and computed-style duration path; include a Teleport+Transition combination; register `e2e/core/test_transition.py` in the `dynamic-control` group in `scripts/run-e2e-tests.sh` and `.github/workflows/ci.yml`
- [x] 5.2 Add a docs_app demo page for `Transition` (fade/slide examples with sample CSS), a static iframe demo under `docs_app/static/_demos/transition/`, a `/sample/transition` route, a navigation link, and an `e2e/docs/test_transition.py` registered in the `docs-demos` group in `scripts/run-e2e-tests.sh` and `.github/workflows/ci.yml`; document the Vue-compatible class protocol, duration resolution order, and the single-child/sequential-replacement semantics

## 6. Validation

- [ ] 6.1 `uv run ruff check .` and `uv run ruff format --check .` pass
- [ ] 6.2 `uv run pyright` passes
- [ ] 6.3 `uv run python -m pytest tests/ --tb=short` passes
- [ ] 6.4 `uv run python -m webcompy generate --app docs_app.bootstrap:app` passes and `openspec validate feat-transition --type change --strict` passes
- [ ] 6.5 All E2E groups pass via `scripts/run-e2e-tests.sh`
