# Design: Docstring Coverage & Enforcement

## Context

See proposal.md — Why. Constraints that shape the approach:

- Implementation lives in `_*.py` private modules behind `__init__.py` re-exports; ruff's pydocstyle presence rules (D100–D107) treat private modules as non-public and never fire there (verified empirically: only `__init__.py` files are flagged).
- The repo already operates a governance-spec + stdlib-checker + CI pattern (`doc-spec-references` / `scripts/check-doc-spec-refs.py`); this change follows it.
- No code in `packages/*/src` introspects `__doc__` (verified by grep), so docstring-only edits are behavior-neutral.
- Existing docstrings use plain prose with no consistent format; ~50 ruff D formatting violations already exist and are auto-fixable.

## Goals / Non-Goals

**Goals:**

- A machine-checkable definition of "public interface" that matches the repo's re-export pattern.
- Presence enforcement in CI from PR-A onward (new code cannot regress coverage).
- Google-style structural quality enforced through mandatory AI-review perspectives.
- Bulk migration delivered as one docstring-only PR whose safety is proven by tooling, not line-by-line review.

**Non-Goals:**

- Structural Args/Returns validation in CI (deferred; see Open Questions).
- Docstring enforcement outside `packages/*/src`.
- Runtime behavior changes of any kind.

## Decisions

### 1. Custom stdlib-only checker instead of ruff D presence rules

`scripts/check-docstrings.py` (stdlib only: `ast`, `tokenize`) owns presence checking. Ruff cannot be configured to treat `_*.py` modules as public, which is where ~95% of the implementation lives. Ruff keeps a role: a formatting-only D subset (D205, D209, D212, D415, D413) validates docstrings that exist, and its autofix cleans up the ~50 existing violations.

Alternatives considered: (a) ruff D only — rejected (blind spot above); (b) `interrogate` — rejected (adds a dependency, and its public/private semantics do not match the re-export pattern; the repo precedent is stdlib-only scripts).

### 2. Public-surface definition: re-export resolution + important-internal allowlist

The checker collects names re-exported by every `__init__.py` of the four packages, follows the import chain to the definition site (handling `as` aliases), and requires docstrings at the definition: class docstring + all public methods/properties for classes; function docstring for functions; PEP 224 attribute docstring (string literal immediately after the assignment) for public module-level constants. Every module under `packages/*/src` also requires a one-line module docstring. A curated `IMPORTANT_INTERNALS` list of dotted paths in the checker adds internal base types that downstream code subclasses or authors interact with; seeded with `Element`, `ComponentStore`, `RenderContext`, `SignalNode` and finalized during PR-A implementation.

Alternative considered: "every public-named definition" (~1,300 items incl. never-re-exported helpers) — rejected as over-broad; the re-export surface (~420 names + members) is the contract users see.

### 3. Baseline ratchet, then strict mode

`scripts/check-docstrings-baseline.txt` (generated via `--write-baseline`) lists current gaps. Violations: (a) undocumented in-scope symbol not in baseline; (b) baseline entry whose symbol now has a docstring (forces removal — monotonic shrink, same philosophy as the markdown-conformance strict-xfail suite). When empty, the file is deleted and the checker runs strict (missing baseline = zero tolerance).

### 4. Enforcement split: CI = presence, AI review = structure

CI verifies a docstring *exists* for every in-scope definition and that no forbidden OpenSpec reference appears. Google-style *structural* validity (Args entries match the signature, Attributes are complete, Returns is meaningful) requires semantic judgment and is owned by the `webcompy-review` skill as 🔴 mandatory perspectives. This keeps the checker simple and deterministic.

### 5. Forbidden OpenSpec references: pattern scan over docstrings AND comments

Docstrings are collected via `ast`; comments via `tokenize` (AST drops comments). Forbidden patterns are an explicit list (`openspec`, `openspec/`, `spec.md`, `tasks.md`, `proposal.md`, `design.md`, change-name references, task numbers) kept small to avoid false positives; references to external standards (RFC, CommonMark, PEP) are explicitly allowed. Exactly one pre-existing violation exists today (`webcompy/app/_app.py:35`) and is removed in PR-A.

### 6. Two-PR delivery

PR-A (governance): spec/checker/baseline/CI/rule docs — small, carefully reviewable; the checker is the only artifact with real logic, and its correctness must not be buried in a bulk diff. PR-B (bulk): all docstrings + baseline removal + change archive. Between the PRs, the baseline keeps CI green while new code is already forced to document.

Alternative considered: one mega-PR — viable (docstring-only diffs are behavior-neutral) but buries checker review in a ~10k-line diff and leaves the repo unenforced until merge. The original 9-PR phased plan was rejected: ratchet bookkeeping per PR buys little when the bulk diff needs no line-by-line review anyway.

### 7. PR-B review aid: AST-equivalence verification

For PR-B review, a verification step strips docstrings/comments from base and head and asserts identical ASTs, proving no logic changed. Combined with ruff/pyright/pytest/e2e green, this replaces line-by-line review of the bulk diff; AI review focuses on the governance content and samples docstring quality.

### 8. Execution model: orchestrator session + `general` subagent batches

Implementation is delegated to the built-in `general` subagent (full tool access) in subsystem batches; the orchestrating session creates artifacts, verifies each batch (checker delta, `git diff --stat`, ruff, spot reads), and manages commits/PRs. Batch order: PR-B covers `ports`, `template`, `signal`+`components`, `app`+`elements`, `ajax`+`aio`+`rpc`+`realtime`, remaining `webcompy` subsystems, then `webcompy_server`, `webcompy_cli`, `webcompy_testing` (module docstrings included per batch). Each subagent returns only a summary; the orchestrator verifies via commands.

## Risks / Trade-offs

- [Checker scope-resolution bug merged to main → CI blocks everyone or silently under-checks] → PR-A is small and review-focused; checker ships with a full baseline so false negatives are visible as baseline size, false positives as immediate CI failures.
- [~10k-line PR-B diff degrades AI review quality] → tooling guarantees (checker completeness, AST equivalence, ruff/pyright/pytest) + targeted AI review of structure samples.
- [Merge conflicts during the PR-B writing window (~250 files touched)] → compress the window, commit per subsystem batch so rebase replays are cheap; docstring conflicts are adjacent-line additions and resolve mechanically.
- [Browser wheel size grows (Google-style docstrings in `webcompy` core)] → order of tens of KB compressed; accepted. Concise summaries keep it bounded.
- [PEP 224 attribute docstrings are unreachable at runtime] → they exist for editors/Sphinx-style tooling and the checker's AST scan; accepted convention.

## Migration Plan

1. PR-A: change artifacts + checker + full baseline + ruff D subset + CI wiring + rule docs (`AGENTS.md`, `openspec/config.yaml`, review skill, local-ci skill) + remove the one existing OpenSpec-reference comment. Merge with baseline green.
2. PR-B: subagent batches author docstrings; each batch shrinks the baseline; final batch deletes the baseline (strict mode), archives this change (spec moves to `openspec/specs/api-docstrings/`), and only then adds the spec's rows to AGENTS.md's File → Spec mapping / invariants / Current Specs (adding them earlier would break `check-doc-spec-refs.py` with a dangling reference).
3. Rollback: both PRs are independently revertible; PR-B is docstring-only.

## Open Questions

- Whether `pydoclint` (or similar) can validate Args/Returns structure against signatures under the re-export pattern well enough to join CI. Spike during PR-A; if unsuitable, AI review remains the structural gate.
