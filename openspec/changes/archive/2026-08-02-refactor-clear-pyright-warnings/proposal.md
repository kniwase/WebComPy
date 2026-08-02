## Why

`uv run pyright` currently reports 70 warnings, all of a single category
(`reportAttributeAccessIssue`), spread across 7 files in `webcompy`,
`webcompy-server`, and `webcompy-cli`. The CI pipeline runs pyright, so these
warnings are persistent noise that obscures real type regressions. The root
causes are narrow and mechanical (intermediate-variable type dispatch,
sentinel values typed as `object`, non-`Optional` attributes assigned `None`
during disposal, dynamic attributes on `ModuleType`/`TypedDict`). Clearing them
now — while the surface is small — keeps the type checker a useful gate instead
of a source of ignored noise.

## What Changes

- Replace intermediate `type(node) is ast.X` dispatch in
  `webcompy/template/_expression.py` with `isinstance(node, ast.X)` so pyright
  can structurally narrow `node` and recognize attribute access (53 warnings).
- Declare `_children: list[ElementAbstract]` on `ElementAbstract` (the abstract
  base) so tree-walking in `SuspenseElement` can access `_children` without
  bypassing the type system (4 warnings).
- Rename `Component.__init_component` (name-mangled private) to
  `Component._init_component` (single-underscore protected) so `SuspenseElement`
  can call it as a legitimate protected method rather than via the
  `_Component__init_component` mangled name (1 warning).
- Introduce a dedicated `_Sentinel` type for the `_UNSET` sentinel in
  `webcompy_cli/config/_build_config.py` and type the `_explicit_*` fields as
  `Literal["cdn", "local"] | _Sentinel`, removing the `object`-typed leak that
  caused "Cannot assign to attribute" warnings (4 warnings).
- Widen the `_root`, `_di_scope`, and `_component_store` attribute declarations
  on `RenderContext` to `... | None` to reflect the post-`dispose()` state
  where they are set to `None` (3 warnings).
- Retype `CallbackConsumerNode._producer` (and its constructor parameter) from
  `SignalNode` to `SignalBase[Any]`, matching the runtime invariant that
  callback producers are always value-bearing signals (2 warnings).
- Fix the SSG lazy-route preload to inspect `page["component"]` (narrowing to
  `LazyComponentGenerator`) and invoke its `_preload()` instead of checking the
  `RouterPage` dict itself — the pre-PR `hasattr(page, "_preload")` guard never
  matched, so lazy routes were never pre-resolved before route generation
  (1 warning).
- Replace direct `app_module.app = app` assignment with
  `cast("Any", app_module).app = app` for dynamically attributed `ModuleType`
  instances (2 warnings).

## Capabilities

### New Capabilities

None.

### Modified Capabilities

This is a type-strictness refactor: runtime behavior is unchanged. The three
internal type/naming contracts it enforces are captured as **ADDED**
requirements (new requirements within existing specs, not modifications of
existing requirement behavior):

- `elements`: Add a requirement that `ElementAbstract` (the element-tree base)
  SHALL declare `_children` so framework tree-walking (Suspense, hydration,
  reconciliation) reaches it uniformly through the base type.
- `reactive`: Add a requirement that `CallbackConsumerNode` SHALL bind to a
  `SignalBase` producer (so `_value` access in dispatch is type-valid).
- `internal-naming`: Add a requirement that framework-internal methods invoked
  from closely-coupled framework code SHALL use the single-underscore protected
  convention (`_name`) rather than name-mangled double-underscore (`__name`).

The remaining fixes (ast `isinstance` dispatch, `_Sentinel` typing,
`RenderContext` disposal `Optional` widening, `cast` for dynamic
`ModuleType` attributes, SSG lazy-route preload target) are local
type-annotation hygiene and are covered as implementation tasks, not spec
requirements.

## Impact

- **Affected code**:
  - `packages/webcompy/src/webcompy/template/_expression.py`
  - `packages/webcompy/src/webcompy/elements/types/_abstract.py`
  - `packages/webcompy/src/webcompy/elements/types/_suspense.py`
  - `packages/webcompy/src/webcompy/components/_component.py`
  - `packages/webcompy/src/webcompy/app/_render_context.py`
  - `packages/webcompy/src/webcompy/signal/_base.py`
  - `packages/webcompy/src/webcompy/router/_pages.py`
  - `packages/webcompy-cli/src/webcompy_cli/config/_build_config.py`
  - `packages/webcompy-cli/src/webcompy_cli/_generate.py`
  - `packages/webcompy-cli/src/webcompy_cli/_server.py`
- **APIs / dependencies**: No public API changes. No dependency additions or
  removals. The `_init_component` rename and `_producer` retyping are internal;
  no downstream call sites outside this repo are known to depend on them.
- **Systems**: None. No runtime behavior, build output, or hydration payload
  changes.
- **Verification**: `uv run pyright` should report `0 errors, 0 warnings`;
  existing unit tests (`uv run python -m pytest tests/`) and E2E suites remain
  green.

## Known Issues Addressed

None. This change does not address any tracked known issue; it clears
type-checker warnings that are not currently catalogued as known issues.

## Non-goals

- Resolving any `reportAttributeAccessIssue` warnings that would require a
  genuine behavioral or API change (none were found during exploration).
- Touching ruff configuration or introducing a `pyrightconfig.json` / pyright
  section in `pyproject.toml` to silence categories. Warnings are resolved in
  code, not by configuration.
- Expanding test coverage or refactoring beyond what is required to satisfy the
  type checker.
- Changing the runtime semantics of `RenderContext.dispose()`, the signal
  dispatch path, the Suspense SSR resolution flow, or the SSG preload behavior.
