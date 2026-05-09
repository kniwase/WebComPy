## 1. Remove _browser/ directory

- [ ] 1.1 Remove `webcompy/_browser/_modules.py`
- [ ] 1.2 Remove `webcompy/_browser/__init__.py`
- [ ] 1.3 Remove `webcompy/_browser/` directory

## 2. Update imports and configuration

- [ ] 2.1 Remove `browser` export from `webcompy/__init__.py`
- [ ] 2.2 Update `pyproject.toml` stubPath: `_browser` → `ports`

## 3. Verify no remaining browser imports

- [ ] 3.1 Run `grep -rn "from webcompy._browser" webcompy/ tests/` — confirm zero matches

## 4. Verification

- [ ] 4.1 Run lint and typecheck
- [ ] 4.2 Run all unit tests
- [ ] 4.3 Run full E2E suite
