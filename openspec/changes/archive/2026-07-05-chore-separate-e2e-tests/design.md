## Context

WebComPy's test suite lives entirely under `tests/`, with three categories co-located:

```
tests/
├── conftest.py            (unit-test fixtures: fake browser, fake document)
├── test_*.py              (~80 unit tests)
├── e2e/                   (framework E2E: 26 test files + my_app/ + conftest.py)
└── e2e_docs/              (docs_app E2E: 8 test files + conftest.py)
```

`pyproject.toml` declares `testpaths = ["tests"]`, which makes pytest discover **all three** categories by default. To run only unit tests, contributors must add `--ignore=tests/e2e --ignore=tests/e2e_docs` — a fact that is easy to forget and not surfaced anywhere in default tooling. To make things worse, E2E tests are syntactically ordinary `test_*.py` files, so `uv run pytest tests/e2e/test_bootstrap.py` "looks correct" and partially works (the conftest provides default ports and timeouts), but it skips the canonical `scripts/run-e2e-tests.sh` flow — missing console-log capture, parallel groups, serving-mode matrix, and tmp-dir isolation. The result is repeated time lost to flaky or incomplete E2E runs.

The CI workflow already separates the two paths structurally: the `test` job uses `--ignore` flags for unit tests, and the `e2e-matrix` job invokes `scripts/run-e2e-tests.sh` per group. But this separation exists only in CI scripts, not in the repository layout — so local developers and AI agents get no signal that E2E is a different beast.

## Goals / Non-Goals

**Goals:**
- Make `uv run pytest` (no arguments) run only unit tests, with zero filter flags.
- Make accidental direct invocation of E2E tests fail loudly with a clear pointer to the canonical script.
- Preserve the existing `scripts/run-e2e-tests.sh` UX (same group names, same `--serving-mode` flag, same console-log capture).
- Keep E2E fixtures, assertions, and `--serving-mode` parametrize behavior untouched.
- Make the separation enforceable via a single root conftest, not via scattered markers that contributors might forget.
- Capture the separation principle as an OpenSpec capability so future changes cannot silently regress it.

**Non-Goals:**
- Refactoring `scripts/run-e2e-tests.sh` beyond path and env-var updates (no new flags, no parallel-mode redesign).
- Migrating unit tests to `tests/unit/` — unit tests stay flat under `tests/`.
- Enforcing `@pytest.mark.e2e` markers as the primary gate. Existing markers stay as informational metadata; the env-var guard is the gate.
- Changing E2E test assertions, fixtures, or the `--serving-mode` parametrize pattern.
- Touching the `webcompy_testing` package API or `pre-commit` hooks.

## Decisions

### Decision 1: Physical directory relocation (Approach A) over config-only filtering (Approach B) or marker-based gating

**Choice:** Move `tests/e2e/` → `e2e/core/` and `tests/e2e_docs/` → `e2e/docs/`.

**Rationale:**
- `testpaths = ["tests"]` then becomes correctly restrictive by default — no `addopts` or `--ignore` flags needed.
- A developer who types `pytest e2e/...` is making an explicit choice; a developer who types `pytest` (the common case) cannot accidentally discover E2E.
- Marker-based gating requires every E2E test file to carry `@pytest.mark.e2e`. Today only 3 of 26 files in `tests/e2e/` have it — enforcing marker coverage is a maintenance burden and a leaky abstraction.
- Config-only filtering (`addopts = ["--ignore=tests/e2e", ...]`) can be overridden from the CLI (`--override-ini`), so it is a soft fence, not a structural one.

**Alternatives considered:**
- **B (addopts only):** Minimal diff, but bypassable and does not solve the "E2E looks like unit tests" confusion.
- **C (marker-based):** Requires auditing every existing E2E file and ongoing discipline. Fragile.
- **B + C hybrid:** Two soft fences still do not signal the directory boundary.

### Decision 2: Guard mechanism — `pytest.UsageError` raised in `pytest_configure`

**Choice:** Add `e2e/conftest.py` with a `pytest_configure` hook that raises `pytest.UsageError` when `WEBCOMPY_RUN_E2E != "1"`.

**Rationale:**
- `pytest_configure` runs early — before test collection — so the abort happens before any fixture tries to spawn a server or allocate a port. This avoids the slow Playwright/server startup that today's accidental invocations incur.
- `pytest.UsageError` is pytest's idiomatic channel for "you used the tool wrong". It produces a clean error message and exit code 2, which is the standard "usage error" signal — distinct from test failures (exit code 1).
- Raising in `pytest_configure` (rather than `pytest_collection_modifyitems`) means the guard fires even if the user passes `--collect-only` or other no-run flags. The error is surfaced at the earliest possible moment.

**Alternatives considered:**
- **`pytest_collection_modifyitems` + `pytest.exit(msg, returncode=2)`:** Fires later, after initial collection walks the filesystem. Slower to surface the error.
- **`@pytest.mark.skip` on every item:** Silent failure — a developer might see "0 passed, 47 skipped" and not realize they did something wrong. Directly contradicts the user's "fail loudly" preference.
- **Warning + allow:** Worst of both worlds: still incurs the slow startup, and the warning is easy to miss in verbose pytest output.

### Decision 3: Opt-in trigger — environment variable only, not CLI flag

**Choice:** `WEBCOMPY_RUN_E2E=1` environment variable. No `--run-e2e` CLI flag.

**Rationale:**
- `scripts/run-e2e-tests.sh` already orchestrates per-group env vars (`E2E_PORT`, `E2E_TMP_DIR`, `CONSOLE_LOG_DIR`, etc.). Adding one more env var fits the existing pattern; a CLI flag would require the script to pass `--run-e2e` through every `uv run python -m pytest` invocation, which is a stylistic mismatch.
- An env var composes cleanly with `uv run` (which inherits the parent shell environment) and with CI (which sets env vars per job).
- A CLI flag would be slightly more discoverable (`pytest --help`), but the guard's error message will explicitly document the env var, so discoverability is preserved without the implementation cost.
- The guard error message will also mention the script as the canonical path, so even developers who never read the spec will be redirected.

**Alternatives considered:**
- **CLI flag `--run-e2e`:** More discoverable, but requires `pytest_addoption` in two conftests (or a shared plugin) and forces the script to thread the flag through.
- **Both env var and CLI flag:** Implementation cost doubles for negligible benefit.

### Decision 4: Single root `e2e/conftest.py` rather than duplicating the guard in both sub-conftests

**Choice:** One new `e2e/conftest.py` containing the guard. Existing `e2e/core/conftest.py` and `e2e/docs/conftest.py` keep their fixture definitions unchanged.

**Rationale:**
- pytest's conftest hierarchy loads parent conftests before child conftests. `e2e/conftest.py` is guaranteed to run its `pytest_configure` before the child conftests' `pytest_configure` (which currently just register the `e2e` marker).
- A single guard is DRY — there is exactly one place to update if the env var name or message ever changes.
- The child conftests already have `pytest_configure` that registers the `e2e` marker. These do not conflict with the root guard (different concerns: marker registration vs collection gating).

**Alternatives considered:**
- **Duplicate the guard in both child conftests:** Violates DRY; if the env var name changes, two files must be updated in lockstep.
- **Move the guard into a `conftest.py` at repo root:** Would affect unit test runs too, forcing the guard to check whether the collection scope is `e2e/`-only. More complex and less localized.

### Decision 5: New capability `test-execution-paths` rather than folding the principle into `e2e-testing`

**Choice:** Introduce `openspec/specs/test-execution-paths/spec.md` as a new capability covering the separation principle and opt-in mechanism.

**Rationale:**
- The separation principle applies symmetrically to unit tests (in `tests/`) and E2E tests (in `e2e/`). Putting it in `e2e-testing` would make the spec asymmetric — it would describe where E2E lives but not where unit tests live.
- A dedicated capability makes the invariant first-class: future changes that propose moving tests between directories will have a single spec to consult.
- `e2e-testing` and `docs-e2e` are then free to focus on E2E-specific behavior (serving modes, console error detection, fixture catalog) without re-stating the directory layout.

**Alternatives considered:**
- **Extend `e2e-testing` with a "tests shall live in `e2e/core/`" requirement:** Asymmetric and conflates layout with behavior.
- **Extend the `architecture` spec:** The architecture spec is high-level and structural; mixing test-path specifics there dilutes its focus.

### Decision 6: Directory naming — `e2e/core/` and `e2e/docs/`

**Choice:** Top-level `e2e/` with two subdirectories `core/` (framework E2E) and `docs/` (docs_app E2E).

**Rationale:**
- A top-level `e2e/` is the most conventional name for E2E test roots in Python projects and reads naturally in commands (`uv run pytest e2e/`).
- `core/` vs `docs/` mirrors the existing conceptual split: "core" tests the framework against a sample app (`my_app`), "docs" tests the documentation site. The existing script group names (`bootstrap-static`, `components`, ... vs `docs-home`, `docs-demos`, ...) already encode this split.
- Naming the subdirectories `e2e/` and `e2e_docs/` (preserving original names) would create `e2e/e2e/` — confusing and redundant.

**Alternatives considered:**
- **`e2e_tests/` top-level + `e2e/` and `e2e_docs/` subdirs:** The `e2e_tests/e2e/` path is awkward.
- **`tests/e2e/` and `tests/e2e_docs/` kept in place, with addopts filtering:** Rejected in Decision 1.
- **`integration/` top-level:** Misleading — these are full E2E browser tests, not integration tests in the usual sense.

### Decision 7: Pyright config — exclude `e2e/**`, do not include `e2e`

**Choice:** Add `e2e/**` to `[tool.pyright].exclude`. Do not add `e2e` to `[tool.pyright].include`.

**Rationale:**
- The existing config already excludes `tests/**` from type checking — E2E tests are not type-checked today (they live under `tests/`). Preserving that behavior means adding `e2e/**` to the exclude list.
- E2E tests heavily use Playwright fixtures, subprocess calls, and dynamic browser APIs that pyright would flag. Type-checking them would produce noise without value.
- The `include` list currently names `tests` (which combined with `exclude = ["tests/**"]` is effectively "look at tests/ but skip everything inside"). We mirror this for `e2e` only if needed — but since `e2e/**` is in `exclude`, there is no need to also list `e2e` in `include`.

## Risks / Trade-offs

- **[Risk] Forgotten reference to old paths in docs or scripts** → Mitigation: The task list includes a grep-based audit step (`grep -rn "tests/e2e"`) before declaring the change complete. The CI workflow and `scripts/run-e2e-tests.sh` are the only executable references; docs are advisory.

- **[Risk] Existing contributors muscle-memory `pytest tests/e2e/...`** → Mitigation: The guard's error message is explicit and points to the script. The first time someone hits it, they learn the new path. This is a one-time cost.

- **[Risk] `pytest_configure` ordering between root and child conftests** → Mitigation: pytest guarantees parent conftests load before children, so `e2e/conftest.py:pytest_configure` runs before `e2e/core/conftest.py:pytest_configure`. The two `pytest_configure` hooks do not conflict (root does the env-var check; child registers a marker). This is verified in the task list by a manual `pytest e2e/` smoke test.

- **[Risk] `WEBCOMPY_RUN_E2E` env var leaks into unit test runs** → Mitigation: The guard lives in `e2e/conftest.py`, which is only loaded when pytest collects tests under `e2e/`. Plain `uv run pytest` (which uses `testpaths = ["tests"]`) never loads `e2e/conftest.py`, so the env var is irrelevant for unit tests.

- **[Risk] CI `e2e-matrix` job fails if env var is not threaded through the script** → Mitigation: The script is the sole entry point for CI E2E runs. The task list explicitly updates `scripts/run-e2e-tests.sh` to inject `WEBCOMPY_RUN_E2E=1` into the `env_cmd` array used by `_run_single`, `_run_single_bg`, and the inline sequential branch.

- **[Trade-off] Two conftest layers (root + child) for E2E** → Accepted. The root conftest is ~15 lines and exists only for the guard. The child conftests remain unchanged in behavior.

- **[Trade-off] `e2e/core/` and `e2e/docs/` are new paths that lookups in archived OpenSpec changes will not match** → Accepted. Archived changes are historical artifacts and should not be rewritten. The active specs (`e2e-testing`, `docs-e2e`) are updated; the new `test-execution-paths` spec is the canonical reference going forward.

- **[Trade-off] Slightly more verbose path in CI matrix `files:` entries** → Accepted. `e2e/core/test_bootstrap.py` is two characters longer than `tests/e2e/test_bootstrap.py`. The clarity gained from the structural separation outweighs the verbosity.

## Migration Plan

This change is implemented in a single PR. There is no gradual rollout — the directory move is atomic.

1. **Move directories** (`tests/e2e/` → `e2e/core/`, `tests/e2e_docs/` → `e2e/docs/`). Use `git mv` to preserve history.
2. **Add `e2e/conftest.py`** with the `pytest_configure` guard.
3. **Update `scripts/run-e2e-tests.sh`** — rewrite group file paths and inject `WEBCOMPY_RUN_E2E=1` into the env_cmd arrays.
4. **Update `.github/workflows/ci.yml`** — rewrite matrix `files:`, drop `--ignore` from the `test` job, update artifact upload paths.
5. **Update `pyproject.toml`** — add `e2e/**` to pyright exclude.
6. **Update documentation** — `AGENTS.md`, `CONTRIBUTING.md`, `CONTRIBUTING.ja.md`, `README.md`, `README.ja.md`.
7. **Update OpenSpec specs** — add `test-execution-paths`, modify `e2e-testing` and `docs-e2e` path references.
8. **Verify** — run `uv run pytest` (unit only), run `uv run pytest e2e/` (expect guard error), run `scripts/run-e2e-tests.sh components` (expect normal E2E flow).

**Rollback strategy:** If the guard or path move causes unexpected CI breakage, revert the merge commit. The directory move is atomic and does not touch test assertions, so rollback restores the pre-change layout exactly.

## Open Questions

- Should the guard's error message also mention the `--serving-mode` flag, or is pointing to the script sufficient? (Decision: point to the script only. The script's `--help` documents `--serving-mode`; duplicating that in the guard message would create a maintenance burden.)
- Should we proactively add `@pytest.mark.e2e` to the 23 E2E files that currently lack it? (Decision: no. The env-var guard is the gate; markers are informational only and adding them is out of scope for this change. Documented as a non-goal.)
