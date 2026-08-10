## 1. Overview spec refresh

- [x] 1.1 Remove the "What WebComPy does not yet provide" paragraph from
  the Purpose section of `openspec/specs/overview/spec.md` (no replacement
  text; per design D2)
- [x] 1.2 Apply the added governance requirement (the overview Purpose
  shall not enumerate missing capabilities; open work and known limitations
  shall instead be tracked in `openspec/config.yaml` (Known Issues) or
  OpenSpec change proposals) to `openspec/specs/overview/spec.md` via the
  archived delta (per design D1)

## 2. Known Issues cleanup in openspec/config.yaml

- [x] 2.1 Remove the Router entry ("RouterView singleton removed ... Router
  singleton remains for now") — Router is per-app via DI
- [x] 2.2 Reword the popstate entry ("Location popstate proxy must be
  manually destroy()ed") — cleanup relies on `BrowserHistoryPort.__del__`,
  which may never run because the browser event target can retain the proxy
  and its callback; the entry stays until an explicit port/context disposal
  path exists
- [x] 2.3 Remove the plugin entry ("No plugin system (noted in README
  ToDo)") — plugin system is implemented
- [x] 2.4 Reword the element-system entry ("No virtual DOM diffing —
  direct DOM manipulation only") to acknowledge key-based reconciliation in
  RepeatElement, and correct the SwitchElement entry to state that it
  replaces children only when branch structures differ (matching structures
  reuse DOM nodes via patching)

## 3. Verification

- [x] 3.1 Run `openspec validate --changes` and confirm this change is
  valid (governance delta per design D1)
- [x] 3.2 Run `python3 scripts/check-doc-spec-refs.py` and confirm it passes
- [x] 3.3 Run `openspec validate --specs` and confirm all main specs remain
  valid

## 4. Review knowledge maintenance

- [x] 4.1 Add the new invariant heading (No Overview Gap List) referencing
  `overview/spec.md` to the Framework Invariants list in `AGENTS.md` and to
  the Critical Framework Invariants section in
  `.opencode/skills/webcompy-review/SKILL.md`
- [x] 4.2 Re-run `python3 scripts/check-doc-spec-refs.py` after the doc
  edits and confirm it passes
- [x] 4.3 Confirm the governance requirement added in task 1.2, including
  its `config.yaml` Known Issues or OpenSpec change proposal tracking policy,
  is synchronized into the review-knowledge references (proposal.md "What
  Changes" and the invariant headings from task 4.1)
