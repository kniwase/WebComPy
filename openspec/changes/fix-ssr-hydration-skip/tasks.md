## 1. Update `WebComPyApp.__init__` to force `_hydrate=False` in non-pyscript environments

- [ ] 1.1 In `webcompy/app/_app.py`, change `self._hydrate = self._config.hydrate` to `self._hydrate = self._config.hydrate and ENVIRONMENT == "pyscript"`
- [ ] 1.2 Verify `ENVIRONMENT` is already imported at the top of `webcompy/app/_app.py` (`from webcompy.utils import ENVIRONMENT`)
- [ ] 1.3 Confirm `WebComPyAppConfig` still accepts `hydrate` field (no change to config dataclass)

## 2. Verify `AppDocumentRoot._render()` guard works as expected

- [ ] 2.1 Run the debug-strict.py trace and confirm T4 (HomePage) is created during the `before await` phase (DI scope alive)
- [ ] 2.2 Confirm `len(html)` is `>= 17000` bytes (post-fix size; pre-fix was 11127)
- [ ] 2.3 Run `webcompy generate` against `docs_app` and grep the SSG output for `is a Python frontend framework` (must return 1)

## 3. Update OpenSpec specs

- [ ] 3.1 In `openspec/specs/app-config/spec.md`, add a `#### Scenario: hydrate is only effective in the pyscript environment` block under the relevant `hydrate` Requirement, stating that `WebComPyApp.__init__` forces `self._hydrate = False` in non-pyscript environments
- [ ] 3.2 In `openspec/specs/app-lifecycle/spec.md`, add a `#### Scenario: SSR/SSG render skips hydration` block stating that `AppDocumentRoot._render()` skips `child._hydrate_node()` in non-pyscript environments because `app._hydrate` is forced to `False`
- [ ] 3.3 In `openspec/specs/async-rendering/spec.md`, add a note (under the "Future Work" or relevant Requirement) that in non-pyscript environments the `await child._render()` path is the only render path; `_hydrate_node` is bypassed

## 4. Verification

- [ ] 4.1 `openspec validate --specs` — all 44 specs pass
- [ ] 4.2 `uv run ruff check .` — no errors
- [ ] 4.3 `uv run pyright` — 0 errors
- [ ] 4.4 `uv run python -m pytest tests/ -k "not e2e" --tb=short` — all unit tests pass
- [ ] 4.5 `scripts/run-e2e-tests.sh --serving-mode=static` — all 14 E2E groups pass
- [ ] 4.6 `scripts/run-e2e-tests.sh --serving-mode=prod` — all 14 E2E groups pass

## 5. Commit and push

- [ ] 5.1 `git add openspec/changes/fix-ssr-hydration-skip/ webcompy/app/_app.py`
- [ ] 5.2 Verify `git diff --cached` shows only the expected files
- [ ] 5.3 `git commit -m "fix: disable hydration in non-pyscript environments for complete SSR/SSG render"`
- [ ] 5.4 Verify pre-commit hooks (ruff / pyright) pass on the commit
- [ ] 5.5 Confirm user before `git push origin feat/async-rendering-pipeline`
