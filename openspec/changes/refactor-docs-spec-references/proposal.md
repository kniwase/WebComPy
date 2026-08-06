## Why

WebComPy's universal documentation documents (AGENTS.md, CONTRIBUTING.md, CONTRIBUTING.ja.md, and the `.opencode/skills/*/SKILL.md` files) transcribe mutable API details that are owned by `openspec/specs/`. When the `Reactive` primitive was renamed to `Signal`, the specs were updated but the transcribed copies drifted — e.g. `Reactive[T]` type annotations and `count = Reactive(0)` remained in archived and live docs. The root cause is that universal docs are expected to be stable and general, yet they duplicate versioned specification content. This change makes `openspec/specs/` the single source of truth by (a) removing stale `Reactive` API references from live docs, (b) de-duplicating transcribed spec details into spec references, and (c) adding a guardrail that detects both dangling spec references and re-introduced stale API names.

## What Changes

- Remove all stale `Reactive` / `ReactiveBase` / `Reactive[...]` API references from live documentation (AGENTS.md, CONTRIBUTING.md, CONTRIBUTING.ja.md, `.opencode/skills/webcompy-component-development/SKILL.md`, `.opencode/skills/webcompy-review/SKILL.md`).
- Reduce the "Framework Invariants" section in AGENTS.md and the "Critical Framework Invariants" section in `webcompy-review/SKILL.md` from transcribed spec detail to invariant headings + spec references. Details that exist only in those sections are promoted into the referenced specs so no requirement is lost.
- Replace the reactive-primitive API enumerations in the Code Conventions sections with references to the relevant specs.
- Add `scripts/check-doc-spec-refs.py` that verifies every `openspec/specs/<name>` reference in the universal docs resolves to an existing spec, and that a blocklist of retired API names (e.g. `webcompy.reactive`, `ReactiveBase`, `Reactive(`, `Reactive[`, `ReactiveNode`, `ReadonlyReactive`) does not reappear in docs.
- Wire the guardrail into the local CI skill and the CI pipeline, and extend AGENTS.md "Review Knowledge Maintenance" so spec add/remove requires updating references and running the checker.
- Do NOT modify archived changes (`openspec/changes/archive/`) — they are historical records.

## Capabilities

### New Capabilities
- `doc-spec-references`: Governs how universal documentation refers to OpenSpec specs. Specs are the single source of truth for requirements; universal docs (AGENTS.md, CONTRIBUTING.*, SKILL.md) SHALL reference specs instead of transcribing spec detail. A checker script SHALL validate that spec references resolve and that retired API names do not reappear.

### Modified Capabilities
- (none — no runtime requirement changes)

## Impact

- `AGENTS.md` — Framework Invariants section reduced to headings + spec references; Code Conventions enumeration replaced with spec references; Review Knowledge Maintenance extended.
- `CONTRIBUTING.md` / `CONTRIBUTING.ja.md` — Code Conventions reactive-primitive enumeration replaced with spec reference.
- `.opencode/skills/webcompy-component-development/SKILL.md` — reactive-primitive enumeration replaced with spec reference.
- `.opencode/skills/webcompy-review/SKILL.md` — Critical Framework Invariants reduced to headings + spec references; stale `Reactive(0)` fixed to `Signal(0)`.
- `scripts/check-doc-spec-refs.py` — new stdlib-only checker script.
- `.github/workflows/ci.yml` — `openspec` job gains a doc-reference validation step.
- `.opencode/skills/webcompy-local-ci/SKILL.md` — gains a doc-reference check step.
- `openspec/specs/` — requirements promoted from the review skill invariants into the owning specs (only where the spec did not already contain them).
- No runtime code in `packages/` changes.