## 1. Fix `_normalize_name()` in wheel builder

- [ ] 1.1 Change `re.sub(r"[-_.]+", "-", name).lower()` to `re.sub(r"[-_.]+", "_", name).lower()` in `_normalize_name()` at `webcompy/cli/_wheel_builder.py:64`
- [ ] 1.2 Update the existing test for `_normalize_name` or `get_wheel_filename` to expect underscores instead of hyphens in the distribution name component

## 2. Update wheel-builder spec

- [ ] 2.1 Update `openspec/specs/wheel-builder/spec.md` — change the "Bundled wheel naming" scenario from `docs-src-25.107.43200-py3-none-any.whl` to `docs_src-25.107.43200-py3-none-any.whl` and the `get_wheel_filename` assertion accordingly
- [ ] 2.2 Update `openspec/specs/wheel-builder/spec.md` — update the "bundling multiple packages" requirement text to say "PEP 427 normalization (underscores, not hyphens)" instead of the current wording
- [ ] 2.3 Update `openspec/specs/cli/spec.md` — verify the CLI spec references to wheel filenames use underscores; update if needed

## 3. Verify the fix

- [ ] 3.1 Run `uv run python -m pytest tests/ --tb=short` to confirm all tests pass
- [ ] 3.2 Run `uv run ruff check .` and `uv run pyright` to confirm lint and type-check pass