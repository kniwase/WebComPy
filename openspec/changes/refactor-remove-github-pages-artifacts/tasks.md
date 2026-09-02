# Tasks: refactor-remove-github-pages-artifacts

## 1. Code removal

- [x] 1.1 Remove the `cname` field from `WebComPyBuildConfig` in `packages/webcompy-cli/src/webcompy_cli/config/_build_config.py`, including its `Args:` and `Attributes:` docstring entries.
- [x] 1.2 Remove the `.nojekyll` touch and the `CNAME` file emission block from `generate_static_site` in `packages/webcompy-cli/src/webcompy_cli/_generate.py`.
- [x] 1.3 Remove `cname="webcompy.net"` from `docs_app/webcompy_config.py`.
- [x] 1.4 Remove the `cname` default assertion from `tests/test_config_dataclasses.py`.

## 2. Verification

- [x] 2.1 Run `uv run ruff check .`, `uv run ruff format --check .`, `uv run pyright`, and `uv run python -m pytest tests/ --tb=short`; fix any fallout.
- [x] 2.2 Run `uv run python -m webcompy generate --config docs_app.webcompy_config` and confirm `docs_app/dist/` is produced without `CNAME` or `.nojekyll` entries and with everything else unchanged.

## 3. Spec sync and archive

- [x] 3.1 Sync the delta specs into `openspec/specs/`: apply the `MODIFIED` blocks from this change; while syncing, normalize the two touched `### MODIFIED: WebComPyBuildConfig ...` headers in `config-separation/spec.md` and `app-config/spec.md` to the canonical `### Requirement:` form (content unchanged, per design).
- [x] 3.2 Confirm `grep -rn "cname\|CNAME\|nojekyll" openspec/specs/` returns no matches and `npx @fission-ai/openspec@latest validate --specs` passes.
- [ ] 3.3 Archive this change with `openspec-archive-change` (or `openspec archive`) so no completed-but-unarchived change remains.
