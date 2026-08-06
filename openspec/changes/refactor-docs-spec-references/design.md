# Design: Doc Spec References

## Context

WebComPy's universal documentation (`AGENTS.md`, `CONTRIBUTING.md`, `CONTRIBUTING.ja.md`, `.opencode/skills/*/SKILL.md`) transcribes mutable specification content that is owned by `openspec/specs/`. When the `Reactive` primitive was renamed to `Signal` (`refactor-rename-reactive-to-signal`), the specs were updated but the transcriptions drifted — `Reactive[T]` type annotations remain in archived change artifacts and `count = Reactive(0)` remains in `webcompy-review/SKILL.md`.

The affected docs fall into two classes:

1. **API-name enumerations** (Code Conventions sections) — `Reactive`, `Computed`, `ReactiveList`, `ReactiveDict` listed as a versioned inventory.
2. **Transcribed spec detail** — the "Framework Invariants" section in `AGENTS.md` (~100 lines) and the "Critical Framework Invariants" section in `webcompy-review/SKILL.md` (~85 lines) restate requirement prose that lives in the specs.

## Goals / Non-Goals

### Goals
- Make `openspec/specs/` the single source of truth for requirements and API naming.
- Remove all stale `Reactive`-family API references from live docs.
- Reduce transcribed spec detail in `AGENTS.md` and `webcompy-review/SKILL.md` to invariant headings + spec references, without losing requirements.
- Add a stdlib-only checker that detects (a) dangling `openspec/specs/<name>` references in docs and (b) re-introduced retired API names.
- Wire the checker into local CI and CI, and extend the spec-maintenance protocol.

### Non-Goals
- Modifying archived changes (`openspec/changes/archive/`) — historical records stay untouched.
- Changing any runtime behavior in `packages/`.
- Renaming `ReactiveList` / `ReactiveDict` (kept by design; "Reactive" describes collection behavior).
- Adding new spec capabilities beyond the `doc-spec-references` governance rule.

## Decisions

### D1: Specs are the single source of truth; universal docs reference, never transcribe

`openspec/specs/` is the authoritative source. `AGENTS.md`, `CONTRIBUTING.*`, and `.opencode/skills/*/SKILL.md` SHALL present requirements as headings + references to the owning spec files. This eliminates the drift class demonstrated by the `Reactive` → `Signal` rename (specs updated, transcriptions stale).

**Alternatives considered:**
- *Keep transcriptions, fix names only* — rejected: the rename drift would recur on the next API change.
- *Generate docs from specs* — rejected: heavy machinery for a small doc set; the docs are already structured as references (File → Spec Mapping, Current Specs).

### D2: Reduce invariants to headings + spec references, promoting spec gaps into the specs

Each invariant in AGENTS.md "Framework Invariants" and review SKILL "Critical Framework Invariants" becomes a heading plus the owning spec(s). Invariant details that exist ONLY in the review skill (not in any spec) are promoted into the owning spec as ADDED requirements so no requirement is lost.

The invariant → spec mapping reuses the existing "File → Spec Mapping" table in AGENTS.md:

| Invariant | Owning spec(s) |
|---|---|
| Dual Environment | `architecture/spec.md` |
| No New Globals | `architecture/spec.md`, `di-scope/spec.md` |
| RenderContext Isolation | `render-context/spec.md` |
| Reactive Contracts | `reactive/spec.md`, `effect/spec.md` |
| Event Handler Leaks | `elements/spec.md` |
| Error Handling | `error-handling/spec.md` |
| Lifecycle Ordering | `components/spec.md`, `async-rendering/spec.md` |
| Async Rendering Pipeline | `async-rendering/spec.md` |
| Async Signal Callback Execution | `async-rendering/spec.md` |
| No Bare Asyncio Scheduling | `async-scheduler/spec.md` |
| Async Dynamic Element Refresh | `async-rendering/spec.md` |
| Hydration / Hydration Guard | `hydration-data-transfer/spec.md`, `elements/spec.md` |
| Hydration Text-Node Normalization | `elements/spec.md` |
| Transfer Codec | `transfer-codec/spec.md` |
| Signal Value Transfer | `signal-value-transfer/spec.md` |
| Payload Compression | `payload-compression/spec.md` |
| ResourcePort | `resource-port/spec.md` |
| RouterView / Depth & Level Reuse | `router/spec.md` |
| FragmentElement | `elements/spec.md` |
| Scoped CSS / Incremental | `scoped-css-incremental/spec.md`, `reactive-scoped-style/spec.md` |
| Head VDOM | `head-vdom/spec.md` |
| Node Cache Strict is-None Check | `elements/spec.md` |
| Composable Usage | `composables/spec.md` |
| Testing Module | `testing-module/spec.md` |
| Inspect CLI Independence | `inspect-cli/spec.md` |
| Template Engine / Binder / Interpolation | `template-engine/spec.md` |
| CSS Text Templates | `template-engine/spec.md` |
| Markdown / GFM / MarkdownFor | `template-engine/spec.md`, `markdown-conformance/spec.md` |
| Forms | `forms/spec.md` |

**Spec-gap promotion** is applied only where the review skill holds detail the spec lacks (e.g. `ErrorBoundaryElement` internal naming, `route_error_deferred`, single-line boundary logging). Most invariants (reactive contracts, async scheduler, hydration text normalization, transfer codec) are already fully specified and only need the reference.

### D3: Checker script with spec-reference resolution + retired-name blocklist

`scripts/check-doc-spec-refs.py` (stdlib `re`, `pathlib`, `sys`) scans the universal docs and validates:

1. **Spec reference resolution**: every `openspec/specs/<name>` (and bare `<name>/spec.md`) reference in the docs resolves to an existing `openspec/specs/<name>/spec.md`.
2. **Retired-name absence**: a blocklist of retired API names (`ReactiveBase`, `Reactive(`, `Reactive[`, `webcompy.reactive`, `ReactiveNode`, `ReactiveEdge`, `ReactiveReceivable`, `ReadonlyReactive`, `__reactive_members__`) must not appear in docs outside the checker itself. The blocklist is a data table in the script; renames add the old name to it (self-maintaining).

The checker is stdlib-only so it runs without `uv sync` in CI's `openspec` job (plain `python3`).

**Alternatives considered:**
- *pytest-based check* — rejected: the `openspec` CI job has no Python env; a standalone script is portable.
- *Curated allow-list of valid names* — rejected: the blocklist is smaller and directly encodes the rename history.

### D4: Maintenance protocol extension

AGENTS.md "Review Knowledge Maintenance" SHALL require, on spec add/remove: update the File → Spec Mapping table, the Current Specs list, every referencing doc, and run `scripts/check-doc-spec-refs.py`. The checker becomes the machine-checkable enforcement of the protocol.

## Risks / Trade-offs

- [Reducing the review skill's transcribed invariants loses reviewer context] → Every invariant keeps its heading and a spec reference; spec-gap details are promoted into the specs (D2), so the reviewer reads the owning spec with the same depth.
- [Spec-gap promotion accidentally rewrites spec requirements] → Promotion is strictly ADDED requirements in the owning spec; existing requirements are untouched.
- [Blocklist gets stale as names change] → The protocol (D4) makes adding the old name to the blocklist part of any rename change; the checker catches docs that still use it.
- [Checker misses inline references in code comments] → The scan targets the named universal docs per the spec; code-comment hygiene is enforced by the review skill, not the checker.

## Migration Plan

1. Fix stale `Reactive` references in the five live docs (Tier A).
2. Reduce the invariants sections to headings + spec references; promote spec gaps (Tier B).
3. Add the checker, wire into local CI and CI, extend the maintenance protocol (Tier C).
4. Run the checker and grep to verify zero retired-name references remain in live docs.
5. Commit; no push, no spec sync, no archive (per user instruction).

## Open Questions

None — scope and approach confirmed with the user.