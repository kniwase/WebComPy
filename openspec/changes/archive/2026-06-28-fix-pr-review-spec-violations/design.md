## Context

The `feat/ui-toolkit-foundation` branch (PR #178) was reviewed by the `ci-review` agent and found to ship four blocking spec violations. The specs already state the correct behavior — the implementation simply has not caught up. The fix is small and targeted: bring the implementation into alignment with the existing specs without changing public-API shape beyond the corrections the spec already calls for.

Concretely, four changes are needed:

1. `use_theme` lives at `webcompy.ui._composables.use_theme` but the spec mandates `webcompy.ui.composables.use_theme` re-exported from `webcompy.ui.theme`.
2. `ThemeManager._system_prefers_dark()` is a stub returning `Theme.SYSTEM`, so `controller.toggle()` from `Theme.SYSTEM` is a no-op. The spec mandates transition to the opposite of `prefers-color-scheme: dark`.
3. `register_lexer(lexer)` has neither `override` nor `source` parameters; duplicate-name registration silently overwrites instead of raising.
4. `LexerInfo` lacks the `source: str` field the spec requires.

Plus one dead entry: `tokens-dark.css` is listed in `webcompy.ui._styles._STYLES_FILES` but the file does not exist on disk (dark tokens were moved to `webcompy/ui/theme/_tokens.py` during the reactive theme migration; the `is_file()` check silently filters it out at runtime).

## Goals / Non-Goals

**Goals:**

- Bring the implementation into compliance with the four existing spec requirements listed above.
- Keep all four fixes narrow, targeted, and individually reviewable.
- Preserve the public API contract: only the previously-private `_composables` path is removed (no external users expected).
- Cover each fix with a focused unit test.
- Pass the full local CI pipeline (lint, format, typecheck, unit tests, `webcompy generate`, `openspec validate`).

**Non-Goals:**

- Not fixing the 🟡 items from the PR #178 review (e.g. `LexerNotFoundError` not listing available lexers, `WebComPyAppConfig.theme` field, missing `webcompy-dynamic` layer, Bash lexer `$VAR` tokenization, `SyntaxHighlighting` docs_app duplication, `_reactive_styles` list location).
- Not changing the 3-state cycle semantics, the cookie persistence behavior, the theme CSS rendering, or the reactive-style primitives.
- Not adding new language lexers.
- Not adding new runtime dependencies.
- Not introducing a `tokens-dark.css` re-introduction; dark tokens stay in Python (`webcompy/ui/theme/_tokens.py`).

## Decisions

### Decision 1: Move `webcompy/ui/_composables/` → `webcompy/ui/composables/`

**Rationale**: Matches the `composables` and `ui-composables` specs verbatim, which already require `webcompy.ui.composables.use_theme`. The underscore-prefixed path was always private; no external users are expected.

**Alternatives considered**:

- **Keep `_composables` private and update specs to match**: simpler code change but yields an awkward public API (`from webcompy.ui._composables import use_theme`) that violates the framework's convention of using underscore-prefixed modules for framework-internal code (cf. `webcompy.ui._styles`).
- **Keep `_composables` and add a deprecated alias**: introduces dead code that we will eventually need to remove.

### Decision 2: Use lazy imports inside `use_theme` to break the circular import

**Rationale**: After `use_theme` is re-exported from `webcompy.ui.theme.__init__`, importing `webcompy.ui.theme` triggers `webcompy.ui.composables._theme`, which imports `ThemeManager` from `webcompy.ui.theme._manager` — a cycle. The previous approach (private `_composables`) avoided the cycle by making the import less likely to happen during package initialization. The cleanest fix that preserves a public API is to move the body imports of `use_theme()` inside the function body. Type hints use `TYPE_CHECKING` for forward references.

**Alternatives considered**:

- **Move the cycle-breaking import to module bottom**: fragile, depends on import order, harder to reason about.
- **`importlib.import_module` inside `use_theme`**: works but adds noise without buying anything over plain function-local imports.

### Decision 3: New `BrowserMediaQueryPort` and `ServerMediaQueryPort` for `prefers-color-scheme: dark`

**Rationale**: The framework's port-abstraction layer is the established pattern for browser-vs-server divergence (see `BrowserCookiePort` / `ServerCookiePort`, `BrowserDOMPort` / `ServerDOMPort`). The new ports follow the same shape: a single `prefers_dark() -> bool` method. The browser side calls `window.matchMedia("(prefers-color-scheme: dark)").matches`. The server side returns `False` (i.e. assume light by default; the user can override via cookie).

**Alternatives considered**:

- **Direct `window.matchMedia` call inside `ThemeManager`**: works in the browser but breaks the dual-environment model and prevents server-side testing of the toggle path.
- **Reuse the existing `DOM_PORT_KEY`**: possible but semantically odd — `matchMedia` is a media-query API, not a DOM-manipulation API.
- **Read the preference once at startup and store on the manager**: not reactive to OS-level changes; the spec is satisfied by a single read at toggle time anyway, so a stateless port call is the simpler model.

**Resolution**: Rename `_system_prefers_dark` → `_system_preferred_theme` (returns `Theme.DARK` or `Theme.LIGHT`, never `Theme.SYSTEM`). `_resolved_toggle_target` now returns the opposite of `_system_preferred_theme()` when current is `Theme.SYSTEM`.

### Decision 4: `register_lexer` signature change

**Rationale**: Direct match to `syntax-highlight-lexers/spec.md:41-43`. The new signature is:

```python
def register_lexer(
    lexer: Lexer,
    *,
    override: bool = False,
    source: str = "custom",
) -> None: ...
```

- If `lexer.name` is already in `_REGISTRY` and `override` is `False`, raise `ValueError`.
- If `override` is `True`, replace the existing entry.
- The `source` value is stored in a parallel `_REGISTRY_SOURCES: dict[str, str]` keyed by `lexer.name` (only the primary name; aliases and file extensions share the same source).
- `register_builtin_lexers()` is updated to pass `source="builtin"` for all three built-ins.

**Alternatives considered**:

- **Store `source` as an attribute on the lexer instance**: requires a mutable field, breaks `Lexer` as a structural Protocol.
- **Store `source` once per `(name, alias, ext)` triple**: redundant; alias and extension entries always share the primary entry's source.

### Decision 5: Add `source: str` field to `LexerInfo`

**Rationale**: Direct match to `syntax-highlight-lexers/spec.md:33`. `list_lexers()` reads from `_REGISTRY_SOURCES` when constructing each `LexerInfo`. Lexers that are not in the sources dict (defensive case) get `source="custom"` as a default.

### Decision 6: Remove `tokens-dark.css` from `_STYLES_FILES`

**Rationale**: The file does not exist. The `is_file()` check inside `get_styles_files()` already filters it out at runtime, so this is a pure cleanup with no user-facing behavior change. The `get_styles_file(name)` validation (which rejects names outside `_STYLES_FILES`) no longer exposes a non-existent filename.

**Alternatives considered**:

- **Re-introduce `tokens-dark.css` as a thin wrapper that imports from Python**: not possible (CSS cannot import from Python).
- **Re-introduce a static `tokens-dark.css` for browsers that don't support reactive styles**: not needed; the framework targets PyScript / evergreen browsers.

## Risks / Trade-offs

- **Breaking the `webcompy.ui._composables.use_theme` import path** → No external users expected (the path was always private). The CI test `test_use_theme_importable_from_public_path` documents the new canonical paths.
- **Lazy imports inside `use_theme` add a per-call cost** → Negligible (the imports are cached after the first call) and the function is not on any hot path.
- **`_system_preferred_theme` falls back to LIGHT on the server** → Acceptable; the server-side initial theme is governed by the cookie, and the spec only requires correct behavior when a `prefers-color-scheme` preference is known. Server-side SSG renders the cookie-driven theme correctly today.
- **`register_lexer(lexer)` raising on duplicate may break user code that relies on silent overwrite** → Acceptable; the spec explicitly forbids silent overwrite, and the framework only calls `register_lexer` from `register_builtin_lexers`, which we control.
- **The new `BrowserMediaQueryPort` extends the ports API surface** → Minimal: a single boolean method, following the existing `BrowserCookiePort` pattern.

## Migration Plan

For users of the framework (not yet released, only docs_app uses it internally):

- Replace `from webcompy.ui._composables import use_theme` with `from webcompy.ui.theme import use_theme` (or `from webcompy.ui.composables import use_theme`). No shim or deprecation period — the old path was never part of the public API.
- Anyone who called `register_lexer(lexer)` twice for the same name (only the framework itself does) and was relying on silent overwrite must now pass `override=True` on the second call. No users in the repo do this.

For `docs_app`: no changes needed; it does not import from `webcompy.ui._composables` and does not call `register_lexer` directly.

## Open Questions

None at this time. All four fixes are mechanical implementation corrections for specs that already state the required behavior.
