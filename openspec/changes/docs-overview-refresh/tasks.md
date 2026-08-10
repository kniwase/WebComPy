## 1. Overview spec refresh

- [ ] 1.1 Remove the "What WebComPy does not yet provide" paragraph from
  the Purpose section of `openspec/specs/overview/spec.md` (no replacement
  text; per design D2)

## 2. Known Issues cleanup in openspec/config.yaml

- [ ] 2.1 Remove the Router entry ("RouterView singleton removed ... Router
  singleton remains for now") — Router is per-app via DI
- [ ] 2.2 Remove the popstate entry ("Location popstate proxy must be
  manually destroy()ed") — cleanup is automatic via `__del__`
- [ ] 2.3 Remove the plugin entry ("No plugin system (noted in README
  ToDo)") — plugin system is implemented
- [ ] 2.4 Reword the element-system entry ("No virtual DOM diffing —
  direct DOM manipulation only") to acknowledge key-based reconciliation in
  RepeatElement while keeping the SwitchElement regeneration note accurate

## 3. Verification

- [ ] 3.1 Run `openspec validate --changes` and confirm this change is
  valid (governance delta per design D1)
- [ ] 3.2 Run `python3 scripts/check-doc-spec-refs.py` and confirm it passes
- [ ] 3.3 Run `openspec validate --specs` and confirm all main specs remain
  valid
