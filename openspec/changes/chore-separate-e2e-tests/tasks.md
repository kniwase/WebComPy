## 1. Directory Relocation

- [ ] 1.1 Move `tests/e2e/` → `e2e/core/` using `git mv` (preserves history; includes `my_app/`, `webcompy_config.py`, `static/`, `conftest.py`, and all `test_*.py`)
- [ ] 1.2 Move `tests/e2e_docs/` → `e2e/docs/` using `git mv` (includes `conftest.py` and all `test_*.py`)
- [ ] 1.3 Verify `tests/` now contains only `conftest.py`, `__init__.py`, and `test_*.py` (no `e2e/` or `e2e_docs/` subdirectories)

## 2. Root E2E Conftest Guard

- [ ] 2.1 Create `e2e/conftest.py` with a `pytest_configure` hook that raises `pytest.UsageError` when `WEBCOMPY_RUN_E2E != "1"`. The error message SHALL mention `scripts/run-e2e-tests.sh` and the `WEBCOMPY_RUN_E2E=1` env var.

## 3. Update scripts/run-e2e-tests.sh

- [ ] 3.1 Update `E2E_GROUPS` array: replace `tests/e2e/test_*.py` paths with `e2e/core/test_*.py`
- [ ] 3.2 Update `DOCS_GROUPS` array: replace `tests/e2e_docs/test_*.py` paths with `e2e/docs/test_*.py`
- [ ] 3.3 Inject `WEBCOMPY_RUN_E2E=1` into the `env_cmd` array in `_run_single()`, `_run_single_bg()`, and the sequential-branch inline invocation (3 locations total)

## 4. Update CI Workflow

- [ ] 4.1 Update `.github/workflows/ci.yml` `e2e-matrix` strategy: rewrite all `files:` entries to use `e2e/core/...` and `e2e/docs/...` paths
- [ ] 4.2 Remove `--ignore=tests/e2e --ignore=tests/e2e_docs` from the `test` job's pytest invocation (the flags are no longer needed since `testpaths = ["tests"]` excludes `e2e/`)
- [ ] 4.3 Update `upload-artifact` paths in `e2e-matrix` job: `tests/e2e/.e2e-server.log` → `e2e/core/.e2e-server.log`, `tests/e2e_docs/.e2e-docs-server.log` → `e2e/docs/.e2e-docs-server.log`

## 5. Update pyproject.toml

- [ ] 5.1 Add `"e2e/**"` to `[tool.pyright].exclude` list (E2E tests are not type-checked, matching the existing `tests/**` exclusion)

## 6. Update Documentation

- [ ] 6.1 Update `AGENTS.md` Commands Reference: change `uv run python -m pytest tests/ --tb=short` to note unit tests only; update E2E script paths; update the File → Spec Mapping table to include `e2e/` → `test-execution-paths` spec; add `test-execution-paths` to Current Specs list
- [ ] 6.2 Update `CONTRIBUTING.md` Testing section: remove `--ignore` references; note that `uv run pytest` runs unit tests only; update E2E path references
- [ ] 6.3 Update `CONTRIBUTING.ja.md` Testing section: same updates as CONTRIBUTING.md
- [ ] 6.4 Update `README.md` if it mentions test paths or commands
- [ ] 6.5 Update `README.ja.md` if it mentions test paths or commands

## 7. Update Agent Configurations

- [ ] 7.1 Update `.opencode/agents/ci-local.md` step 4: remove `--ignore=tests/e2e --ignore=tests/e2e_docs` from the pytest command (now just `uv run python -m pytest tests/ --tb=short`)
- [ ] 7.2 Update `.opencode/agents/ci-review.md`: add `test-execution-paths` to the File → Spec Mapping table for `tests/` and `e2e/` directories; add `test-execution-paths` to the Current Specs list

## 8. Verification

- [ ] 8.1 Run `uv run pytest --tb=short` (no path args) — verify only unit tests run, no E2E collection attempted
- [ ] 8.2 Run `uv run pytest e2e/` — verify `pytest.UsageError` is raised with a message mentioning `scripts/run-e2e-tests.sh` and `WEBCOMPY_RUN_E2E=1`
- [ ] 8.3 Run `WEBCOMPY_RUN_E2E=1 uv run pytest e2e/core/test_bootstrap.py --serving-mode=static --tb=short` — verify the guard passes and E2E fixtures work
- [ ] 8.4 Run `scripts/run-e2e-tests.sh components --serving-mode=static` — verify the canonical E2E flow works end-to-end
- [ ] 8.5 Run `uv run ruff check .` and `uv run ruff format --check .` — verify lint passes
- [ ] 8.6 Run `npx @fission-ai/openspec@latest validate --specs` and `--changes` — verify OpenSpec validation passes
- [ ] 8.7 Grep audit: `grep -rn "tests/e2e" . --include="*.py" --include="*.yml" --include="*.toml" --include="*.sh" --include="*.md"` — verify only `openspec/changes/archive/` matches remain (historical artifacts)
