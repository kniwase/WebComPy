## Context

`uv run pyright` reports 70 warnings, all `reportAttributeAccessIssue`, across
7 files. There is no `pyrightconfig.json` and no pyright section in
`pyproject.toml`, so these come from pyright's default rule set. The warnings
cluster into six root causes (see proposal). Five are mechanical; two involve a
small type-contract decision that warrants recording here:

1. Where to declare `_children` so tree-walking code can reach it through the
   `ElementAbstract` base type.
2. How to type `CallbackConsumerNode._producer` so `_value` access is
   type-valid.

The rest (ast dispatch, sentinel typing, `RenderContext` disposal, dynamic
`ModuleType`/`TypedDict` attributes) are local and unambiguous.

## Goals / Non-Goals

**Goals:**

- Reduce `uv run pyright` to `0 errors, 0 warnings` without suppressing rules.
- Keep runtime behavior, public API, build output, and hydration payloads
  byte-for-byte equivalent.
- Make each fix local and reviewable; avoid coupling unrelated modules.

**Non-Goals:**

- Introducing a `pyrightconfig.json` or tuning rule severities.
- Refactoring the ast evaluator, signal graph, or Suspense flow beyond what the
  type checker demands.
- Expanding public surface (no new public methods, types, or config options).

## Decisions

### Decision 1: `_children` declared on `ElementAbstract`

**Choice.** Add `_children: list[ElementAbstract] = []` (with `# noqa: RUF012`)
to `ElementAbstract` in `elements/types/_abstract.py`, and remove the now-
redundant class-level default on `ElementWithChildren` only if it duplicates the
base (keep subclass overrides where subclasses redeclare a more specific type).

**Rationale.** `SuspenseElement._collect_pending_coroutines` and
`_hydrate_node` walk an element tree typed as `ElementAbstract`. At runtime
every concrete element that can hold children (`ElementWithChildren`,
`DynamicElement`, `Component`) has `_children`; only `TextElement` is a true
leaf. Declaring the attribute on the base makes the type reflect the runtime
invariant and lets pyright accept `element._children` without `hasattr`
bypasses or cross-module `isinstance` coupling.

**Alternatives considered.**

- `isinstance(element, (ElementWithChildren, Component))` narrowing in Suspense.
  Rejected: `Component` extends `ElementBase`, not `ElementWithChildren`, so the
  guard must enumerate two unrelated concrete classes, increasing coupling and
  fragility (any new child-bearing element type would have to update the guard).
- A shared `Protocol`/ABC for child-bearing elements. Rejected: more machinery
  than the problem warrants; the runtime reality is "all non-leaf elements have
  `_children`," which the base declaration captures directly.

**Caveat.** `TextElement` will inherit an empty `_children` list. This is
semantically loose but harmless: nothing iterates `TextElement._children`, and
the default `[]` (class attribute) is never mutated on instances.

### Decision 2: Rename `Component.__init_component` to `_init_component`

**Choice.** Rename the name-mangled `__init_component` to the single-underscore
`_init_component`. Update the internal call sites in `_component.py`
(definition + two internal callers) and the external caller in `_suspense.py`
(`component._Component__init_component(...)` → `component._init_component(...)`).

**Rationale.** `SuspenseElement` legitimately re-initializes a component after
resolving its async template during SSR. Reaching through the mangled name
`_Component__init_component` is a code smell and the direct cause of the pyright
warning (`Cannot access attribute "_Component__init_component"`). A
single-underscore name signals "protected — callable from closely-coupled
framework code," which matches actual usage.

**Alternatives considered.**

- `cast(Component, component)` at the call site. Rejected: silences the warning
  but preserves the mangled-name smell; the cast hides intent rather than
  expressing it.
- Promote to a public `init_component`. Rejected: it is not part of the intended
  public API; exposing it invites misuse.

### Decision 3: Retype `CallbackConsumerNode._producer` to `SignalBase[Any]`

**Choice.** Change the `_producer` field annotation and the `__init__`
parameter from `SignalNode` to `SignalBase[Any]`.

**Rationale.** `CallbackConsumerNode` is constructed only in
`SignalBase.on_before_updating` / `on_after_updating`, passing `self` (a
`SignalBase`) as the producer. `Computed` — the only other producer that
appears in dispatch logic — is itself `Computed(SignalBase[V])`. So at runtime
`_producer` is always a value-bearing `SignalBase`, and `_dispatch` reads
`self._producer._value` (defined on `SignalBase`, not on the `SignalNode`
base). `_CallbackMixin` does not redeclare `_producer`, so the change is
localized to `CallbackConsumerNode`.

**Alternatives considered.**

- `isinstance(self._producer, SignalBase)` guard inside `_dispatch`. Rejected:
  adds a runtime branch to express an invariant that is already guaranteed by
  construction.
- `cast(SignalBase[Any], self._producer)` at the access sites. Rejected: weaker
  type safety; the field annotation should reflect the truth.

**Compatibility.** `producer_add_live_consumer` and
`producer_update_value_version` accept `SignalNode`; since `SignalBase` is a
subclass of `SignalNode`, the retyping is assignment-compatible at all existing
call sites.

### Decision 4: `_Sentinel` type for `_UNSET` in `WebComPyBuildConfig`

**Choice.** Define a `_Sentinel` sentinel class and type `_UNSET: _Sentinel =
_Sentinel()`. Type `_explicit_wasm_serving` / `_explicit_runtime_serving` as
`Literal["cdn", "local"] | _Sentinel`.

**Rationale.** Today `_explicit_*` is typed `Literal["cdn", "local"] | object`,
and `_UNSET` is a bare `object()`. Because `_UNSET` is `object`, the
`self._explicit_* is _UNSET` check does not narrow, so the value assigned back
to `wasm_serving` / `runtime_serving` retains an `object` component, which
pyright reports as "Cannot assign to attribute." A dedicated `_Sentinel` type
and `isinstance(self._explicit_*, _Sentinel)` guards remove the `object` leak:
pyright narrows the non-sentinel branch to `Literal["cdn", "local"]` exactly.
(An `is _UNSET` identity check does not narrow here, because `_Sentinel` is a
class type and pyright cannot exclude other potential instances from the
identity comparison; `isinstance` narrowing works on the type itself.)

### Decision 5: `RenderContext` disposal attributes widened to `| None`

**Choice.** Annotate `_root`, `_di_scope`, and `_component_store` as
`... | None` (initialized non-`None` in `__init__`, set to `None` in
`dispose()`).

**Rationale.** `dispose()` explicitly nulls these to break reference cycles.
The current declarations forbid `None`, so the assignment is flagged. Widening
the declared type matches the actual lifecycle. Read sites (properties,
`dispose()` cleanup, `_register_ports` in both render contexts) add
`assert self._root is not None` / `assert self._di_scope is not None`
narrowing: pyright cannot infer that `_check_disposed()` raises after disposal,
so the asserts are required for the widened types to type-check. The asserts
are harmless at runtime — they can only fire if a read slips past the disposed
guard, which is a bug.

### Decision 6: `RouterPage._preload` as an optional TypedDict key + `"_preload" in page`

**Choice.** Add `_preload: Callable[[], None]` to `RouterPage` (the
`total=False` portion) and change the SSG guard in `cli/_generate.py` from
`hasattr(page, "_preload")` to `"_preload" in page`.

**Rationale.** `hasattr` on a `TypedDict` does not narrow; the `in` operator
does. Declaring the key makes the access type-valid and documents the optional
contract.

### Decision 7: `cast` for dynamic `ModuleType` attributes

**Choice.** Replace `app_module.app = app` with
`cast("Any", app_module).app = app` in `cli/_generate.py` and `cli/_server.py`.

**Rationale.** `types.ModuleType` does not declare an `app` attribute, and these
modules are synthetic (`ModuleType("_webcompy_app")`). `setattr(app_module,
"app", app)` was the first choice, but ruff's B010 rule rejects `setattr` with a
constant attribute name ("not any safer than normal property access"),
reintroducing the exact warning we are removing. A `cast("Any", ...)` on the
module is the sanctioned last-resort for genuinely dynamic attributes: it
expresses "this module dynamically carries an `app` attribute" at the type
level while satisfying both pyright and ruff. It sits next to the existing
`app_module.__file__ = ...` assignment (a known module attribute, hence not
flagged).

### Decision 8: `isinstance` dispatch in `_expression.py`

**Choice.** Replace `node_type = type(node)` + `if node_type is ast.X:` with
`if isinstance(node, ast.X):` throughout `_eval_node`.

**Rationale.** pyright narrows `node` on `isinstance` but cannot narrow through
an intermediate `type(node)` variable. `isinstance` is the idiomatic,
performance-equivalent form (CPython optimizes `isinstance` with no MRO walk for
exact matches). No `match` statement rewrite is needed; the diff stays minimal.

## Risks / Trade-offs

- **`_children` on base slightly loosens the leaf contract** → Mitigation: the
  attribute defaults to an empty list and is never mutated on `TextElement`;
  the existing `# noqa: RUF012` convention for mutable class defaults is reused.
  No code iterates children of a leaf.
- **`_init_component` rename could miss a call site** → Mitigation: a repo-wide
  search confirms exactly four references (3 internal + 1 in `_suspense.py`);
  the rename is mechanical and `pyright`/tests will catch any miss.
- **Retyping `_producer` to `SignalBase[Any]` loses element-of-generic
  precision** → Mitigation: `_value` is read as `Any` already; the
  `SignalBase[Any]` is strictly more precise than the previous `SignalNode`
  (which lacked `_value` entirely). No generic precision is lost that wasn't
  already absent.
- **`_Sentinel` is a new private type** → Mitigation: module-private (leading
  underscore), no public surface change.

## Migration Plan

No deployment or data migration. The change is purely source-level. Rollback is
`git revert`. Verification:

```bash
uv run ruff check . && uv run ruff format --check .
uv run pyright                       # expect: 0 errors, 0 warnings
uv run python -m pytest tests/ --tb=short
scripts/run-e2e-tests.sh             # confirm Suspense SSR + SSG preload paths
```

## Open Questions

None. All design decisions were resolved during exploration; the remaining work
is mechanical implementation captured in `tasks.md`.
