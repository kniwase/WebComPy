## Context

The current `ci.yml` workflow defines 7 jobs plus a review job. Among them, `lint` depends on `openspec`, and `e2e` depends on `lint` and `test`, creating a critical path that serializes execution unnecessarily. The `e2e` job runs all 15 E2E test files against both `prod` and `static` serving modes in a single runner, making it the dominant wall-clock bottleneck (often 6-8 minutes). Other pre-check jobs (`typecheck`, `generate`, `test`) run in isolation but still duplicate `uv sync` work.

## Goals / Non-Goals

**Goals:**
- Run `openspec`, `lint`, `typecheck`, `generate`, and `test` fully in parallel with no cross-dependencies.
- Split E2E tests into a matrix of functional categories × serving modes, each running on an independent runner.
- Deduplicate `uv sync` and `playwright install` via a reusable composite action that leverages the built-in `setup-uv` cache.
- Guard the heavy E2E matrix so it only starts when all lightweight pre-checks succeed (skip on failure to avoid wasting runner minutes).

**Non-Goals:**
- Adding new E2E tests or changing test logic.
- Replacing GitHub Actions with another CI provider.
- Changing the `deploy-pages.yml` workflow.

## Decisions

### Decision 1: Use matrix strategy for E2E grouping
**Rationale**: GitHub Actions matrix natively spins up independent runners for each combination. Grouping by functional category keeps each job focused and avoids the overhead of one-file-per-job.

**Alternative considered**: File-level matrix (15 files × 2 modes = 30 jobs). Rejected because it exceeds the typical free-plan parallel limit (20) and incurs excessive server-startup overhead relative to test runtime.

### Decision 2: Move `serving_mode` from pytest parametrize to CLI option
**Rationale**: The existing `serving_mode` fixture parametrize forces every test to run both modes in the same job. By exposing a CLI option (e.g., `--serving-mode=prod`), the CI matrix can assign one mode per matrix axis, cutting per-job test count in half and avoiding re-running server setup twice.

**Alternative considered**: Keep parametrize and rely on `pytest -k "[prod]"`. Rejected because it is brittle (relies on pytest internal naming) and still generates both variants.

### Decision 3: Reusable composite action over artifact caching
**Rationale**: GitHub composite actions cleanly encapsulate `setup-uv` + `uv sync` + `playwright install`. While `upload-artifact`/`download-artifact` could share a pre-built venv, `uv` cache + `setup-uv` caching is already fast enough; composite action is simpler and avoids artifact size limits.

**Alternative considered**: Cache `.venv` as an artifact. Rejected because venvs are not portable across runner images (ABI/path issues).

### Decision 4: Keep `review` job depending on `e2e` (matrix)
**Rationale**: The review job requires all checks to complete. With matrix jobs, using `needs: [e2e]` where `e2e` is the matrix job ID automatically waits for all matrix instances. This is the native GitHub Actions behavior.

## Risks / Trade-offs

- [Risk] `prod_server` and `static_server` session fixtures assume a hardcoded port (8088), which is safe across independent runners but would break if jobs were ever collocated. **Mitigation**: Document that matrix runners are independent; do not change port assignment in this change.
- [Risk] Removing `needs: [lint, test]` from `e2e` means failing lint will no longer cancel `e2e` before it starts. **Mitigation**: Add `if: ${{ !failure() && !cancelled() }}` to the E2E job so it is skipped if any pre-check failed.
- [Trade-off] More parallel runners mean higher total compute minutes (same work, just distributed). The acceleration benefit outweighs the cost for developer velocity.

## Migration Plan

1. Create the composite action.
2. Update `ci.yml` job dependencies and add E2E matrix.
3. Update `conftest.py` to support `--serving-mode` CLI option (default both for backward compatibility).
4. Run a test PR to verify matrix jobs execute correctly and review job aggregates results.
5. Archive the change.
