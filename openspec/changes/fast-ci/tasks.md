- [x] Task 1: Create reusable composite action `.github/actions/setup-environment/action.yml`
  - Encapsulate `actions/setup-node@v4`, `astral-sh/setup-uv@v6` with `cache: true`, `uv sync`, and `playwright install chromium`
  - Accept optional `uv-sync-args` input (e.g. `--all-groups`) with default empty

- [x] Task 2: Update `.github/workflows/ci.yml` — parallel pre-checks and E2E matrix
  - Remove `needs: [openspec]` from `lint`
  - Remove `needs: [lint, test]` from `e2e`
  - Remove `needs: [...]` from `review` and change to `needs: [openspec, lint, typecheck, generate, test, e2e]`
  - Replace single `e2e` job with matrix strategy:
    - `group`: `[bootstrap-static, components, reactive-lists, dynamic-control, router, interaction]`
    - `serving_mode`: `[prod, static]`
    - Map each group to pytest file/directory patterns (e.g. `test_bootstrap.py test_static_site.py` for `bootstrap-static`)
  - Add `if: ${{ !failure() && !cancelled() }}` on the E2E matrix job

- [x] Task 3: Update `tests/e2e/conftest.py` to support `--serving-mode` CLI option
  - Add `pytest_addoption` registering `--serving-mode {prod,static}`
  - Change `serving_mode` fixture to read CLI option / env var; when provided yield that single mode, otherwise parametrize both `["prod", "static"]` for backward compatibility

- [x] Task 4: Verify locally that E2E tests pass with `--serving-mode=prod` and `--serving-mode=static`
