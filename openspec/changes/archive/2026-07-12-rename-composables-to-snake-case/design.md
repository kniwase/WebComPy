## Context

WebComPy's public composable API currently mixes snake_case (`use_state`, `use_reactive_list`, `use_async_result`) and legacy camelCase (`useRouter`, `useAsync`, `useAsyncResult`). The previous `feat/signal-composable` change introduced `use_async_result` as the canonical name but kept `useAsyncResult` as a backward-compatible alias. The remaining camelCase names are inconsistent with PEP 8 and the rest of the framework. Since the framework is pre-stable, this change completes the migration in one sweep without aliases.

A comprehensive search of `packages/` confirmed only three camelCase composables remain: `useRouter`, `useAsync`, and `useAsyncResult`. All other camelCase identifiers are DOM API wrappers (e.g., `setAttribute`, `appendChild`) that intentionally mirror browser APIs and are out of scope.

## Goals / Non-Goals

**Goals:**
- Rename all public composables to snake_case: `use_router`, `use_async`, `use_async_result`.
- Remove the `useAsyncResult` camelCase alias entirely.
- Update all internal call sites, tests, E2E pages, demos, CLI templates, and main OpenSpec specs to match the new names.
- Keep the implementation, signatures, lifecycle behavior, and import paths otherwise identical.
- Add naming convention guidance to project documentation so future public APIs follow Python (PEP 8) conventions, with explicit exceptions for browser/DOM-aligned terms.
- Address two minor type annotation regressions flagged by the AI review of PR #198:
  - Restore `dict` type annotation on `navigation._open_states` in `docs_app/components/navigation.py`.
  - Restore the named keyword parameter for `FizzbuzzList` in `packages/webcompy-cli/src/webcompy_cli/template_data/app/components/fizzbuzz.py`.

**Non-Goals:**
- No backward-compatible aliases.
- No semantic changes to the composables.
- No new features or composables.
- No renaming of DOM API wrappers (e.g., `setAttribute`, `appendChild`).
- No edits to archived OpenSpec changes.

## Decisions

**1. Rename functions in-place rather than adding aliases and deprecating.**
- Rationale: The project is pre-stable and explicitly accepts breaking changes. Aliases would extend the migration window and leave a mixed convention in the codebase.
- Alternative considered: Keep camelCase aliases for one release cycle. Rejected because it contradicts the "complete migration" goal and the framework is not yet stable.

**2. Update `webcompy.router` to export `use_router` instead of `useRouter`.**
- The router composable is a thin `inject(RouterKey)` wrapper. The rename is mechanical and does not affect its behavior.

**3. Update `webcompy.components._hooks` so that `use_async` is the canonical name and `useAsync` is removed.**
- `useAsync` is a fire-and-forget wrapper around `AsyncWrapper()` + `on_after_rendering()`. The rename is purely mechanical.

**4. Remove `useAsyncResult` from `webcompy.components._hooks` and keep only `use_async_result`.**
- The canonical function already exists; the alias is only the extra wrapper. Removing it reduces API surface.

**5. Update main OpenSpec specs (`composables`, `async`, `router`, `overview`) but leave archived change files untouched.**
- The main specs are the source of truth for the current API. Archived changes are historical records and should not be rewritten.

**6. Use a global search-and-replace over all code files, followed by `ruff` and `pyright` verification.**
- A mechanical rename is safe as long as we verify with lint and type checking. The function signatures remain unchanged.

**7. Add a naming convention section to the project contribution/reference documentation.**
- Rationale: Prevents future API drift. The rule is: Python public functions/variables use `snake_case`; classes use `PascalCase`; DOM/browser API wrappers may use `camelCase` when mirroring standard web API names (e.g., `addEventListener`).
- Location: Add a short paragraph to `AGENTS.md` under Code Conventions, or to `CONTRIBUTING.md` if one exists. `AGENTS.md` is the agent reference and is the appropriate place for rules enforced by AI reviewers.

**8. Address the two AI review items from PR #198 as cleanup.**
- Rationale: They are minor type-annotation regressions introduced by the previous PR. Fixing them here avoids a dedicated follow-up PR and aligns with the broader cleanup theme.
- `docs_app/components/navigation.py`: restore `dict[str, bool]` (or equivalent) type annotation on `_open_states`.
- `packages/webcompy-cli/src/webcompy_cli/template_data/app/components/fizzbuzz.py`: restore the named keyword argument for the `FizzbuzzList` parameter.

## Risks / Trade-offs

- **[Risk] User code relying on the old camelCase names breaks immediately.** → Mitigation: Accepted and documented as a breaking change for a pre-stable framework. No aliases provided.
- **[Risk] A missed call site or spec reference remains camelCase.** → Mitigation: Use `rg`/`grep` to find all occurrences, then run `ruff check`, `pyright`, and the full test suite to catch stragglers.
- **[Risk] E2E or demo pages that reference the old names fail to render.** → Mitigation: E2E tests cover the affected pages; run the full E2E matrix after renaming.

## Migration Plan

1. Rename functions in `packages/webcompy/src/webcompy/router/_composables.py` and `packages/webcompy/src/webcompy/components/_hooks.py`.
2. Update all imports and call sites across `packages/`, `tests/`, `e2e/`, `docs_app/`, and CLI templates.
3. Update main OpenSpec specs and `AGENTS.md` reference tables.
4. Add naming convention guidance to `AGENTS.md`.
5. Fix the two AI review items from PR #198.
6. Run `ruff check`, `ruff format`, `pyright`, unit tests, and E2E tests.
7. Archive the change after merge.

## Open Questions

(none — the scope and approach are clear.)
