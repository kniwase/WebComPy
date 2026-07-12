## Why

A comprehensive search of `packages/` confirmed only three camelCase composables remain: `useRouter`, `useAsync`, and `useAsyncResult`. All other camelCase function identifiers are DOM API wrappers (e.g., `setAttribute`, `appendChild`) that intentionally mirror browser APIs and are therefore out of scope.

## What Changes

- **Rename `useRouter()` → `use_router()`** in `webcompy.router` (and any public re-exports).
- **Rename `useAsync()` → `use_async()`** in `webcompy.components` and re-export paths.
- **Remove the `useAsyncResult()` camelCase alias**; keep only `use_async_result()` as the canonical name.
- Update all internal framework call sites, tests, E2E pages, demos, and CLI templates to use the new names.
- Update main OpenSpec specs that reference the old camelCase names (`composables`, `async`, `router`, `overview`) so the specification matches the public API.
- **Add naming convention guidance**: Document that all future WebComPy public APIs should follow Python naming conventions (PEP 8), while frontend-specific terms that are intentionally aligned with browser/DOM standards (e.g., DOM method wrappers) may remain camelCase.
- **BREAKING**: User code calling `useRouter()`, `useAsync()`, or `useAsyncResult()` will break. No aliases are provided.

### Bonus Scope: Address AI Review Items from PR #198

The previous PR `feat/signal-composable` (PR #198) was approved by AI review with two minor "Should Improve" items that do not affect framework behavior but are worth fixing in this cleanup change:

1. **Restore the lost type annotation on `navigation._open_states`** in `docs_app/components/navigation.py`.
2. **Restore the named keyword parameter for `FizzbuzzList`** in `packages/webcompy-cli/src/webcompy_cli/template_data/app/components/fizzbuzz.py` (changed from named to positional in the previous PR).

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `composables`: Rename `useRouter()` to `use_router()`, `useAsync()` to `use_async()`, and remove the `useAsyncResult()` alias from the requirements.
- `async`: Remove the `useAsyncResult()` alias requirement; only `use_async_result()` remains canonical.
- `router`: Update the `useRouter()` composable reference to `use_router()`.
- `overview`: Update any example snippets that use the old camelCase names.

## Impact

- Public API: `webcompy.router.use_router`, `webcompy.components.use_async`, `webcompy.components.use_async_result`.
- All internal usages of the old names in `packages/`, `docs_app/`, `e2e/`, and `tests/`.
- OpenSpec main specs and agent reference tables in `AGENTS.md`.
- Archived OpenSpec changes are **not** modified; they remain historical records.

## Known Issues Addressed

(none — this is a naming consistency cleanup unrelated to the listed known issues.)

## Non-goals

- No backward-compatible aliases will be kept. The framework is pre-stable and this change is a complete migration.
- No behavior changes to the composables themselves (semantics, signatures, lifecycle timing remain identical).
- No new composables or features are introduced.
- DOM API wrappers (e.g., `setAttribute`, `appendChild`) are NOT renamed; they intentionally mirror browser APIs.
- Archived OpenSpec changes are not retroactively edited.
