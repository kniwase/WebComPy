## 1. Remove _browser/ directory

- [ ] 1.1 Remove `webcompy/_browser/_modules.py`
- [ ] 1.2 Remove `webcompy/_browser/__init__.py`
- [ ] 1.3 Remove `webcompy/_browser/` directory

## 2. Update imports and configuration

- [ ] 2.1 Remove `browser` export from `webcompy/__init__.py`
- [ ] 2.2 Update `pyproject.toml` stubPath: `_browser` → `ports`

## 3. Verification

- [ ] 3.1 Run lint and typecheck
- [ ] 3.2 Run all unit tests
- [ ] 3.3 Run full E2E suite
