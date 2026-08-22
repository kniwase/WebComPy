## Why

WebComPy's public API surface (~420 re-exported names across four packages, plus their public members) is almost entirely undocumented: an AST scan shows roughly 11% of public-named functions and 9% of public classes carry docstrings, and most modules have no module docstring. For a framework, docstrings are the primary in-editor API reference, and there is no rule or tooling that keeps coverage from regressing. Ruff's pydocstyle presence rules cannot help here: implementation lives in `_*.py` private modules behind `__init__.py` re-exports, which ruff treats as private and skips.

## What Changes

- Introduce a docstring requirement for all public interfaces (names re-exported through package `__init__.py` files and their public members), plus an explicit allowlist of important internal interfaces (e.g. `Element`, `ComponentStore`, `RenderContext`, `SignalNode`).
- Adopt Google-style docstrings: module docstrings are summary-only; public functions/methods document `Args:`/`Returns:` (and `Raises:` when non-obvious); classes document construction `Args:` and `Attributes:`; public module-level constants carry PEP 224-style attribute docstrings.
- Forbid references to OpenSpec artifacts (spec/change names, `openspec/` paths, requirement/scenario IDs, task numbers) in docstrings and code comments. References to external standards (RFC, CommonMark, PEP, ...) remain allowed.
- Add a stdlib-only checker `scripts/check-docstrings.py` that resolves the public surface by following re-exports into private modules, verifies docstring presence (including PEP 224 attribute docstrings), and scans docstrings/comments for forbidden OpenSpec references. A baseline file keeps CI green during migration and ratchets downward; when the baseline is empty the file is removed and the checker runs strict.
- Enable a formatting-only subset of ruff's pydocstyle rules (D205/D209/D212/D415 etc.) so existing and new docstrings stay well-formed; presence checking stays with the custom checker.
- Wire the checker into CI (openspec job) and the `webcompy-local-ci` skill, and record the rule in `AGENTS.md`, `openspec/config.yaml`, and the `webcompy-review` skill as a mandatory AI-review perspective.
- Deliver in two PRs: (A) governance + checker + full baseline, (B) bulk docstring authoring until the baseline is empty. PR-B's review relies on tooling guarantees (checker completeness, AST-equivalence of code, ruff/pyright/pytest green) rather than line-by-line reading.

## Capabilities

### New Capabilities

- `api-docstrings`: Docstring coverage and content governance for public interfaces — scope definition (re-export resolution + important-internal allowlist), Google-style content requirements, PEP 224 attribute docstrings, the OpenSpec-reference ban, exemptions, and the checker/baseline enforcement contract.

### Modified Capabilities

(none)

## Impact

- **Code**: docstring-only additions across `packages/*/src` (~250 files); one existing comment referencing an OpenSpec change path in `webcompy/app/_app.py` is removed. No behavior changes — no code path introspects `__doc__`.
- **Tooling**: new `scripts/check-docstrings.py` + baseline; ruff config gains a D-rule formatting subset; CI openspec job gains a checker step.
- **Docs/governance**: `AGENTS.md` code conventions amend the "no comments unless requested" rule to carve out required docstrings; `openspec/config.yaml` context/rules updated; `.opencode/skills/webcompy-review/SKILL.md` gains mandatory review perspectives; `.opencode/skills/webcompy-local-ci/SKILL.md` gains the checker step.
- **Distribution**: Google-style docstrings add modest weight to the browser-shipped `webcompy` wheel (order of tens of KB compressed); accepted and recorded in design.md.
- **Out of scope for enforcement**: `tests/`, `e2e/`, `docs_app/` (one-line docstrings on test functions remain encouraged but are not CI-enforced).

## Known Issues Addressed

None.

## Non-goals

- Enforcing docstrings in `tests/`, `e2e/`, or `docs_app/`.
- Translating docstrings (all docstrings are English, per language rules).
- Structural Args/Returns validation in CI (e.g. via pydoclint) — Google-style structural correctness is an AI-review responsibility; a spike may revisit this.
- Runtime behavior changes, API renames, or documentation-site content changes.
- Docstring coverage tooling for downstream (user) projects.
