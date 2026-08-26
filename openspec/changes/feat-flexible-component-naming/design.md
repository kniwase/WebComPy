# Design: Flexible Component Naming

## Context

`define_component` (packages/webcompy/src/webcompy/components/_generator.py) currently requires a positional `name`, validates it with `_validate_custom_element_name`, and enforces `component_def.__name__ == kebab_to_pascal(name)` inside the decorator, raising a mismatch error otherwise. The codebase accumulated verbose function names purely to satisfy this rule. See proposal.md — Why.

## Goals / Non-Goals

**Goals**

- Single decorator-factory call form (`@define_component(...)`) with an optional `custom_element_name`.
- Derivation path: tag = `pascal_to_kebab(function.__name__)`, validated only on the derived result.
- Decoupling path: explicit tag never compared to the function name.
- Codebase sweep so all three usage styles are exercised by real code and tests.

**Non-Goals**

- Bare undecorated form support (explicitly rejected for implementation simplicity).
- Changes to registration/hydration, observed attributes, display kwarg semantics.
- Prop→attribute reflection.

## Decisions

### D1: Always-called decorator factory with optional first argument

```python
def define_component(
    custom_element_name: str | None = None,
    *,
    observed_attributes: Iterable[str] = (),
    display: ComponentDisplay | None = None,
) -> Callable[[FuncComponentDef[PropsType]], ComponentGenerator[PropsType]]:
```

- The first parameter is positional-or-keyword (no `/` marker) so both `@define_component("x")` and `@define_component(custom_element_name="x")` work; existing positional calls remain source-compatible.
- One signature, no `@overload`; return type stays "decorator" on every path, keeping `.pyi` and IDE behavior simple.
- Alternatives considered:
  - *Bare callable dispatch* (`@define_component` decorating directly): rejected — doubles code paths, needs three overloads, complicates re-decoration guards. User decision.
  - *Positional-only argument*: rejected — keyword use adds readability at call sites at no cost.

### D2: Validation timing split between factory call and decoration

- At factory call time: validate explicit tag (if given), normalize observed_attributes, validate display — same as today.
- At decoration time (inside the returned decorator): derive the tag from `component_def.__name__` when `custom_element_name is None`, run `_validate_custom_element_name(derived)` with derived-oriented error messages, and check the re-decoration guard.
- Rationale: the function name is only known when the decorator actually applies; moving derivation there keeps factory-call validation eager (fail before decoration) for everything knowable early.

### D3: Round-trip check removed

Only `_validate_custom_element_name` rules apply to the derived value (lowercase regex + hyphen + reserved list). `kebab_to_pascal(derived) == function.__name__` is dropped. Consequence: `HTTPRequest` → `<http-request>` is accepted, which is desirable under flexible naming. Reserved names still fail in derived mode (`FontFace` → `font-face`).

### D4: Error catalog and message strategy

| # | Failure | Detection | Message guidance |
|---|---|---|---|
| 1 | Derived name lacks hyphen (`App` → `app`) | naming rules | rename to multi-word PascalCase **or** pass explicit tag |
| 2 | Derived name reserved (`FontFace` → `font-face`) | reserved list | same as #1 |
| 3 | Derived name fails regex (`my_card`, `_Card`) | naming rules | rename to PascalCase **or** pass explicit tag |
| 4 | Explicit tag invalid | naming rules | existing message, unchanged |
| 5 | Duplicate tag within app | existing registry check (unchanged) | existing message |
| 6 | Re-decoration of a marked object | marker check | "already a component definition" |
| 7 | Bare undecorator application | N/A — Python binds the function; factory call omitted | covered by D1 contract tests + docs; no runtime detection needed beyond the natural failure mode |

The old mismatch error (#8 in exploration) disappears entirely. Derived-mode errors mention both remedies (rename or explicit tag); explicit-mode errors keep today's wording.

Re-decoration guard (#6): applying the returned decorator to an object having `__webcompy_component_definition__` raises instead of corrupting state. This replaces the protection the mismatch check accidentally provided.

### D5: Codebase sweep pattern classification

Existing definitions are classified into four patterns:

- **A — name already derives**: function name equals `pascal_to_kebab(tag)` round-trip. Convert to the omitted/kwargs-only form (`@define_component()`, `@define_component(observed_attributes=..., ...)`). Scope: `docs_app/components|layout|templates|pages`, framework components (`ui/code_block/_component.py`), CLI scaffold `template_data/app/components/*.py`, and **all unit-test definitions whose names derive naturally** (full conversion per user decision).
- **B — verbose name mirroring the tag**: demo apps with doubled qualifiers. Rename the function simpler, keep the explicit tag unchanged: `HelloWorldApp`→`HelloWorld`, `FetchSampleApp`→`FetchSample`, `MatplotlibSampleApp`→`MatplotlibSample`, `TeleportDemoApp`→`TeleportDemo`, `TransitionDemoApp`→`TransitionDemo`. Suffix `-page` stays (role information). Final list confirmed during task execution.
- **C — live spec examples using the bare form**: update example snippets in `openspec/specs/reactive-scoped-style/spec.md` and any other live spec using bare `@define_component` above examples to the called form. Archived changes are historical records — untouched.
- **D — documentation prose**: `docs_app/documents/custom_elements.md` (rewrite naming-rules section: single-word failure now surfaces only via derivation error, acronyms allowed, migration section updated), `quickstart.md`.

Pattern A conversions double as proof that derivation works across the entire test suite and build (E2E groups cover docs_app; CLI scaffold is exercised where feasible).

### D6: Definition key stability

`ComponentGenerator.definition_key` embeds `custom_element_name` (`webcompy-v1:{tag}:{attrs}`). Tags themselves do not change for sweep-pattern B (only Python function names change), so hydration transfer metadata remains stable across the refactor. No format change.

## Risks / Trade-offs

- [Silent import-order regression if module-level generators register under changed names] → Pattern B renames never change tags; tags drive registration, DOM, scoped CSS selectors, and definition keys.
- [Users relying on mismatch errors as typo protection] → Mitigated by duplicate-tag detection (D4 #5) and documented behavior; explicit tags remain validated.
- [Large diff from full test conversion] → Mechanical `@define_component("x-y")` → `@define_component()` rewrite only where the round-trip holds; verified mechanically (regex/script-assisted) plus full pytest run.
- [Scaffold templates drift] → template_data files converted in the same change; `webcompy init` output verified by inspection or targeted check.

## Migration Plan

1. Implement decorator changes with backward-compatible called forms (no existing valid caller breaks).
2. Sweep codebase per D5 (A/B/C/D).
3. Update docstring + `.pyi` if present; run lint/pyright/pytest/E2E groups.
4. Rollback: revert commit; no data or wire-format changes exist.

## Open Questions

None. Sweep target lists (pattern B exact set) may be finalized during task execution within the stated criteria.
