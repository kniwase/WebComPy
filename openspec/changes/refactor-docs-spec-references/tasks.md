# Tasks: Doc Spec References

## 1. Tier A — Stale Reactive references

- [x] 1.1 Fix `count = Reactive(0)` → `count = Signal(0)` in `.opencode/skills/webcompy-review/SKILL.md:106`
- [x] 1.2 Replace the reactive-primitive API enumeration in `AGENTS.md:107` with a spec reference (reactive/spec.md, composables/spec.md)
- [x] 1.3 Replace the reactive-primitive API enumeration in `CONTRIBUTING.md:233` with a spec reference
- [x] 1.4 Replace the reactive-primitive API enumeration in `CONTRIBUTING.ja.md:236` with a spec reference
- [x] 1.5 Replace the reactive-primitive API enumeration in `.opencode/skills/webcompy-component-development/SKILL.md:21` with a spec reference

## 2. Tier B — De-duplicate transcribed spec detail

- [x] 2.1 Reduce AGENTS.md "Framework Invariants" (lines ~137-241) to invariant headings + owning spec references, keeping the "See review SKILL" pointer
- [x] 2.2 Reduce `.opencode/skills/webcompy-review/SKILL.md` "Critical Framework Invariants" (lines ~68-153) to invariant headings + owning spec references
- [x] 2.3 Identify review-skill invariant details not present in any spec and promote them as ADDED requirements into the owning specs (spec-gap promotion)
- [x] 2.4 Update the review SKILL's Critical Framework Invariants maintenance note in AGENTS.md "Review Knowledge Maintenance" to reference the new doc-spec-references governance

## 3. Tier C — Guardrail

- [x] 3.1 Create `scripts/check-doc-spec-refs.py` (stdlib-only): validates `openspec/specs/<name>` references in the universal docs resolve to existing specs, and that the retired-name blocklist (`ReactiveBase`, `Reactive(`, `Reactive[`, `webcompy.reactive`, `ReactiveNode`, `ReactiveEdge`, `ReactiveReceivable`, `ReadonlyReactive`, `__reactive_members__`) does not appear in docs; exits non-zero with a concise report on violation
- [x] 3.2 Wire the checker into `.github/workflows/ci.yml` `openspec` job (plain `python3 scripts/check-doc-spec-refs.py`)
- [x] 3.3 Add the checker step to `.opencode/skills/webcompy-local-ci/SKILL.md`
- [x] 3.4 Extend AGENTS.md "Review Knowledge Maintenance" to require updating referencing docs and running the checker on spec add/remove

## 4. Verification

- [x] 4.1 Run `python3 scripts/check-doc-spec-refs.py` — exits 0 with no findings
- [x] 4.2 Grep live docs for `Reactive(` / `Reactive[` / `webcompy.reactive` / `ReactiveBase` — zero matches
- [x] 4.3 Run `uv run ruff check .` and `uv run pyright` — pass
- [x] 4.4 Run `openspec validate --specs` and `openspec validate --changes` — pass
- [x] 4.5 Commit on branch `refactor/docs-spec-references` with `refactor:` message and `Co-Authored-By` footer (no push, no PR, no spec sync, no archive)