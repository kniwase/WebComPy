## 1. Add browser/server media query ports

- [ ] 1.1 Add `BrowserMediaQueryPort` (in `webcompy/ports/_browser/_media_query.py`) with `prefers_dark() -> bool` method that reads `window.matchMedia("(prefers-color-scheme: dark)").matches`
- [ ] 1.2 Add `ServerMediaQueryPort` (in `webcompy/ports/_server/_media_query.py`) with `prefers_dark() -> bool` method that returns `False`
- [ ] 1.3 Add `MEDIA_QUERY_PORT_KEY` to `webcompy/ports/_keys.py` and re-export from `webcompy/ports/__init__.py`
- [ ] 1.4 Register the new port implementations in `webcompy/ports/_provider.py` (or equivalent DI registration)

## 2. Implement `_system_preferred_theme()` in `ThemeManager`

- [ ] 2.1 Rename `_system_prefers_dark()` → `_system_preferred_theme()` in `webcompy/ui/theme/_manager.py`
- [ ] 2.2 Make the new function inject `MEDIA_QUERY_PORT_KEY` and call `prefers_dark()`; return `Theme.DARK` if true else `Theme.LIGHT`. Fall back to `Theme.LIGHT` if the port is not registered (SSR)
- [ ] 2.3 Update `_resolved_toggle_target()` so that when current is `Theme.SYSTEM`, the target is the *opposite* of `_system_preferred_theme()` (DARK → LIGHT, LIGHT → DARK)
- [ ] 2.4 Add a `from __future__ import annotations` and `TYPE_CHECKING` block if needed to keep type hints clean

## 3. Move `_composables` to public `composables` and re-export `use_theme`

- [ ] 3.1 `git mv webcompy/ui/_composables webcompy/ui/composables`
- [ ] 3.2 Update all internal imports throughout `webcompy/`, `tests/`, and any other references from `webcompy.ui._composables` to `webcompy.ui.composables`
- [ ] 3.3 Convert `webcompy/ui/composables/_theme.py` to use lazy (function-local) imports inside `use_theme()` to break the circular import; keep type hints under `TYPE_CHECKING`
- [ ] 3.4 Add `use_theme` to `webcompy/ui/theme/__init__.py` as a re-export
- [ ] 3.5 Run a final grep to confirm no remaining `webcompy.ui._composables` references exist

## 4. Extend `register_lexer` signature and `LexerInfo`

- [ ] 4.1 Add `_REGISTRY_SOURCES: dict[str, str] = {}` at module level in `webcompy/ui/code_block/lexers/_registry.py`
- [ ] 4.2 Change `register_lexer(lexer)` to `register_lexer(lexer, *, override: bool = False, source: str = "custom")`; raise `ValueError` on duplicate `lexer.name` unless `override=True`; populate `_REGISTRY_SOURCES[lexer.name] = source`
- [ ] 4.3 Add `source: str` field to `LexerInfo` in `webcompy/ui/code_block/lexers/_base.py`
- [ ] 4.4 Update `list_lexers()` to populate `source` from `_REGISTRY_SOURCES` (default to `"custom"` for any lexer missing from the dict)
- [ ] 4.5 Update `register_builtin_lexers()` to pass `source="builtin"` for `PythonLexer`, `BashLexer`, and `TomlLexer`
- [ ] 4.6 Update `reset_lexer_registry()` (if present) or add one to clear both `_REGISTRY` and `_REGISTRY_SOURCES` so tests start clean

## 5. Remove dead `tokens-dark.css` entry

- [ ] 5.1 Remove `"tokens-dark.css"` from `_STYLES_FILES` tuple in `webcompy/ui/_styles/__init__.py`
- [ ] 5.2 Confirm `get_styles_file("tokens-dark.css")` now returns `None` (rejected by name allowlist)

## 6. Add tests

- [ ] 6.1 `tests/test_use_theme_imports.py` (new): `use_theme` is importable from `webcompy.ui.theme` and `webcompy.ui.composables`; `webcompy.ui._composables` does not exist
- [ ] 6.2 `tests/test_theme.py`: add scenarios for `controller.toggle()` from `Theme.SYSTEM` with dark pref → `Theme.LIGHT`, and with light pref → `Theme.DARK`; mock `MEDIA_QUERY_PORT_KEY` via `inject()` override
- [ ] 6.3 `tests/test_lexer_registry.py` (new or updated): `register_lexer(lexer)` twice without `override` raises `ValueError`; `register_lexer(lexer, override=True)` succeeds; `LexerInfo.source` is set; `register_builtin_lexers` populates `source == "builtin"`
- [ ] 6.4 `tests/test_ui_styles.py`: add assertion that `"tokens-dark.css"` is not in `_STYLES_FILES`

## 7. Run verification

- [ ] 7.1 `uv run ruff check .` — must pass
- [ ] 7.2 `uv run ruff format --check .` — must pass
- [ ] 7.3 `uv run pyright` — 0 errors (pre-existing warnings acceptable)
- [ ] 7.4 `uv run python -m pytest tests/ --tb=short` — all tests pass
- [ ] 7.5 `uv run python -m webcompy generate --config docs_app.webcompy_config` — exit 0
- [ ] 7.6 `openspec validate --type change --strict` and `openspec validate --type spec --strict` — pass

## 8. Commit, archive, push, update PR

- [ ] 8.1 Stage and commit the fix as `fix: address PR review spec violations (use_theme path, theme toggle, lexer registry)` with the Co-Authored-By footer
- [ ] 8.2 Run `openspec archive fix-pr-review-spec-violations` to move the change to `archive/2026-06-28-fix-pr-review-spec-violations/`
- [ ] 8.3 `git push origin feat/ui-toolkit-foundation` (no force — 11 new commits will be fast-forwarded)
- [ ] 8.4 Update PR #178 body to the previously-approved description via `gh pr edit 178 --body-file ...`
