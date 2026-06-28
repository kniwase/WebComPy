## Why

The `feat/ui-toolkit-foundation` branch (PR #178) was reviewed and four blocking spec violations / bugs were found. The PR cannot merge as-is because it ships an API that does not match its own spec (`register_lexer`, `LexerInfo`, `use_theme` import path) and a theme manager that gets stuck on `Theme.SYSTEM` when the user toggles. This change addresses all four blocking items, plus one trivial cleanup, so the PR can proceed.

## What Changes

- **Move `webcompy/ui/_composables/` to `webcompy/ui/composables/`** (public API) and re-export `use_theme` from `webcompy/ui/theme/__init__.py`. Move the `use_theme` body imports to lazy imports inside the function to break the resulting circular import.
- **Implement `ThemeManager._system_preferred_theme()`** so `controller.toggle()` correctly transitions from `Theme.SYSTEM` to `Theme.DARK` or `Theme.LIGHT` based on the user's `prefers-color-scheme: dark` media query (browser) or `LIGHT` default (SSR). Rename the function from `_system_prefers_dark` and have it return `Theme.DARK` or `Theme.LIGHT` (never `Theme.SYSTEM`).
- **Extend `register_lexer` signature** to `register_lexer(lexer, *, override: bool = False, source: str = "custom")`. Raise `ValueError` on duplicate name unless `override=True`. Store `source` in a parallel `_REGISTRY_SOURCES: dict[str, str]`. Update `register_builtin_lexers()` to pass `source="builtin"`.
- **Add `source: str` field to `LexerInfo`**. Populate it from `_REGISTRY_SOURCES` inside `list_lexers()`.
- **Remove `tokens-dark.css` from `_STYLES_FILES`** in `webcompy/ui/_styles/__init__.py`. The file does not exist (dark tokens were moved to `webcompy/ui/theme/_tokens.py` in the reactive theme migration). The `get_styles_files()` function silently filtered it out via the `is_file()` check, so no user-facing behavior changes; this just removes a dead entry.

No new runtime dependencies. No user-facing behavior changes except:
- `use_theme` becomes importable from `webcompy.ui.theme` (additive — the previous private path is removed).
- `ThemeManager.toggle()` from `Theme.SYSTEM` now actually changes the theme (previously it stayed on `SYSTEM`).
- Calling `register_lexer(lexer)` twice for the same `lexer.name` now raises `ValueError` (previously it silently overwrote).

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- **`composables`**: add a clarifying requirement that `use_theme` is importable from the public `webcompy.ui.theme` and `webcompy.ui.composables` paths, that both imports refer to the same function, and that the previously private `webcompy.ui._composables` module is not part of the public API. The other three blocking items from the PR #178 review are implementation corrections for specs that already state the correct behavior:
  - `ui-composables/spec.md:27-29` already requires `toggle()` from `Theme.SYSTEM` to switch to the opposite of `prefers-color-scheme`.
  - `syntax-highlight-lexers/spec.md:41-43` already requires the `register_lexer(lexer, *, override=False, source="custom")` signature with `ValueError` on duplicate.
  - `syntax-highlight-lexers/spec.md:33` already requires `LexerInfo` to have a `source: str` field.

## Impact

- **Public API**: `webcompy.ui.theme.use_theme` becomes a public symbol. `webcompy.ui._composables.use_theme` is removed.
- **New browser port**: `BrowserMediaQueryPort` (or extension of an existing port) for `prefers-color-scheme: dark` detection. Server side returns `LIGHT` default.
- **Tests**: new tests for each fix; existing `test_theme.py` and `test_lexer_registry.py` updated.
- **docs_app**: not affected (does not import from `webcompy.ui._composables` or call `register_lexer` directly).
- **Other in-progress PRs**: none reference `use_theme` import path or `register_lexer` signature.

## Non-goals

- Not changing the 3-state theme cycle semantics (`light → dark → system → light`).
- Not changing the cookie persistence behavior.
- Not fixing the 🟡 items from the PR #178 review (e.g. `LexerNotFoundError` not listing available lexers, `WebComPyAppConfig.theme` field, missing `webcompy-dynamic` layer, Bash lexer `$VAR` tokenization, `SyntaxHighlighting` docs_app duplication, `_reactive_styles` list location). These are tracked for follow-up.
- Not adding `!important` flags or changing the theme CSS rendering logic.
- Not adding new language lexers.

## Known Issues Addressed

This change directly resolves four spec violations found during the PR #178 review:

1. `use_theme` was defined at `webcompy.ui._composables.use_theme` instead of `webcompy.ui.composables.use_theme` and was not re-exported from `webcompy.ui.theme`, violating the `composables` and `ui-composables` specs.
2. `ThemeManager._system_prefers_dark()` was a stub returning `Theme.SYSTEM`, so `controller.toggle()` from `Theme.SYSTEM` was a no-op, violating the `theme-system` spec scenario "WHEN current is SYSTEM and OS preference is light, toggle SHALL set theme to DARK".
3. `register_lexer(lexer)` had no `override` or `source` parameters, violating the `syntax-highlight-lexers` spec.
4. `LexerInfo` lacked the `source: str` field, violating the `syntax-highlight-lexers` spec.

It also removes the dead `tokens-dark.css` entry in `_STYLES_FILES` (file does not exist since the reactive theme migration).
