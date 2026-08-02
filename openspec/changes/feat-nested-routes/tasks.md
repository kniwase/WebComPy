# Tasks

## 1. Page Tree and Chain Flattening

- [x] 1.1 Add recursive `children: list[RouterPage]` to `RouterPage` in `packages/webcompy/src/webcompy/router/_pages.py`
- [x] 1.2 In `packages/webcompy/src/webcompy/router/_router.py`, implement tree walking in `_generate_routes`: produce per-leaf chains of route nodes (design D1) while keeping `__routes__` as full-path 5-tuples (SSG contract); path joining with slash normalization; index (`""`) handling
- [x] 1.3 Unit tests: flattening (nested, index, deep nesting), path joining edge cases, bare-parent-without-index yields no leaf entry, flat pages produce single-level chains

## 2. Chain Matching (`current_match`)

- [x] 2.1 Implement `RouteMatch` and `Router.current_match` as a Computed over the history signal (design D2): per-level segment matching, accumulated params, query/state capture, first-definition-wins, `None` on no match
- [x] 2.2 Unit tests: chain matching with params at multiple levels, overlapping sibling patterns (`/docs/new` vs `/docs/{name}`), index vs `{param}` collision order, query parsing, hash and history modes

## 3. Depth-Aware RouterView with Level Reuse

- [x] 3.1 Rewrite `packages/webcompy/src/webcompy/router/_view.py`: depth via RouterView-ancestor count in `_on_set_parent` (D3); per-level holder Computed with instance preservation under the identical-match rule (D4); render via `SwitchElement` tracking the holder; proper destruction of replaced instances (component/DI-scope disposal path)
- [x] 3.2 Remove or repurpose `Router.__cases__` for rendering (keep `__default__`); verify `RouterContext` construction per level (accumulated params, D4)
- [x] 3.3 Unit tests (with `webcompy_testing`): sibling navigation preserves parent instance (setup not re-run, DOM state kept); param change remounts leaf only; query change remounts; ancestor param change remounts all descendants; view deeper than chain renders empty; multiple same-depth views

## 4. Lazy, Hooks, SSG Integration

- [x] 4.1 Update `preload_lazy_routes` to traverse the full page tree; verify `RouterLink` hover preload resolves nested full paths
- [x] 4.2 Verify hooks fire once per nested navigation (extend `tests/` router-hook tests)
- [x] 4.3 Verify `uv run python -m webcompy generate` produces static HTML for nested full paths on a fixture app (SSG contract unchanged)

## 5. E2E and Verification

- [x] 5.1 Add e2e app pages under `e2e/core/my_app/pages/`: a nested docs-layout scenario (sidebar state preserved across sibling navigation, leaf remount on param change observable via setup counter) + Playwright tests under `e2e/core/`
- [x] 5.2 Run `uv run ruff check .`, `uv run ruff format --check .`, `uv run pyright`, `uv run python -m pytest tests/ --tb=short` (existing flat-router tests MUST pass unmodified)
- [x] 5.3 Run relevant e2e groups via `scripts/run-e2e-tests.sh` and `uv run python -m webcompy generate` on docs_app

## 6. Spec and Housekeeping

- [ ] 6.1 Apply the delta to `openspec/specs/router/spec.md` (archive/sync flow); update the spec's "does not yet provide" note about nested routes
- [ ] 6.2 Check `AGENTS.md` File→Spec Mapping and `.opencode/skills/webcompy-review/SKILL.md` for stale router statements (e.g., flat-route assumptions)
