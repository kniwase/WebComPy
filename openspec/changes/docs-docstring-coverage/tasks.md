# Tasks: Docstring Coverage & Enforcement

## 1. PR-A: Checker tooling (delegate to `general` subagent)

- [x] 1.1 Implement `scripts/check-docstrings.py` per design.md: re-export resolution to definition sites, presence checks (module/class/function/method/property/PEP 224 constant), exemption rules, forbidden OpenSpec-reference scan over docstrings (`ast`) and comments (`tokenize`), `--write-baseline` mode, strict mode when baseline absent. Seed `IMPORTANT_INTERNALS` after reviewing `Element`, `ComponentStore`, `RenderContext`, `SignalNode`
- [x] 1.2 Generate the full baseline (`--write-baseline`) and commit it; verify checker exits 0 with baseline and non-zero on a deliberately undocumented test symbol
- [x] 1.3 Add ruff D formatting subset (D205, D209, D212, D413, D415) to `pyproject.toml`; run `ruff check --fix` for the ~50 pre-existing formatting violations
- [x] 1.4 Remove the OpenSpec change-path reference in `packages/webcompy/src/webcompy/app/_app.py:35` (reword the comment to describe the code only)
- [x] 1.5 Spike: evaluate `pydoclint` for Args/Returns structural validation under the re-export pattern; record outcome in design.md (adopt or stay with AI-review-only)
- [x] 1.6 Adopt pydoclint: dev dependency (`pydoclint>=0.9.1`), tuned `[tool.pydoclint]` config in pyproject.toml (`style=google`, `arg-type-hints-in-docstring=false`, `check-return-types=false`), `ci.yml` lint-job step with artifact log, fixed 10 existing structural violations so the four src trees are clean
- [x] 1.7 Address PR-A review feedback: restore the `Raises:` section on `parse_css` (transitive raise is contractual; exclude that file from pydoclint DOC502 with rationale) and document the checker/AI-review enforcement split for forbidden OpenSpec references in the checker docstring, spec scenarios, and design.md

## 2. PR-A: Governance wiring (orchestrator session)

- [x] 2.1 Amend `AGENTS.md` code conventions: docstring requirement + OpenSpec-reference ban, carving docstrings out of "no comments unless requested" (no spec-path references yet — the spec does not exist in `openspec/specs/` until archive)
- [x] 2.2 Update `openspec/config.yaml` context conventions line and add a docstring rule entry
- [x] 2.3 Add mandatory 🔴 perspectives to `.opencode/skills/webcompy-review/SKILL.md`: docstring presence + Google-style structural completeness; OpenSpec-reference ban
- [x] 2.4 Add the checker step to `.opencode/skills/webcompy-local-ci/SKILL.md`
- [x] 2.5 Add a checker step to the openspec job in `.github/workflows/ci.yml`
- [x] 2.6 Verify locally: checker green with baseline, `ruff check`, `ruff format --check`, `pyright`, `pytest tests/`, `openspec validate`; open PR-A

## 3. PR-B: `webcompy` core docstrings (delegate per batch; each batch shrinks the baseline)

- [x] 3.1 Batch `ports` (~125 docstrings incl. module docstrings); checker delta verified
- [ ] 3.2 Batch `template` (~125)
- [ ] 3.3 Batch `signal` + `components` (~165)
- [ ] 3.4 Batch `app` + `elements` (~145)
- [ ] 3.5 Batch `ajax` + `aio` + `rpc` + `realtime` (~190; includes the new `rpc/_contracts.py` module merged to main — split rpc into its own batch if it runs long)
- [ ] 3.6 Batch `forms` + `router` + `hydration` + `ui` + `di` + `plugin` + `storage` + `exception` + `utils` + `events` (~150)

## 4. PR-B: Server-side packages (delegate per batch)

- [ ] 4.1 Batch `webcompy_server` (~150 incl. module docstrings)
- [ ] 4.2 Batch `webcompy_cli` (~140 incl. module docstrings)
- [ ] 4.3 Batch `webcompy_testing` (~115 incl. module docstrings)

## 5. PR-B: Finalization

- [ ] 5.1 Sweep: checker reports zero violations; delete the baseline file (strict mode)
- [ ] 5.2 AST-equivalence verification (strip docstrings/comments from base and head, compare ASTs) as PR-B review evidence
- [ ] 5.3 Full local CI: ruff, pyright, pytest, `webcompy generate`; open PR-B
- [ ] 5.4 Archive this change; then add `api-docstrings` rows to AGENTS.md File → Spec mapping, Framework Invariants, and Current Specs; run `python3 scripts/check-doc-spec-refs.py`
