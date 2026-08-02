# Proposal: Loop Metadata for `{% for %}` and Explicit Unsupported-Directive Errors

## Why

The template engine's `{% for %}` blocks currently expose only the loop variable(s), forcing developers to hand-roll positional logic (e.g., row numbering, first/last styling) via wrapper objects or external `Computed` values — a frequent need that Jinja2 solves with the `loop` metadata object. Additionally, directive-like `{% %}` spans that are not supported (e.g., `{% extends %}`, `{% block %}`, or typos such as `{% endfo %}`) currently pass through the parser silently and are emitted as literal text, violating the framework's "errors, not silent output" principle and producing confusing output instead of actionable failures.

At the same time, the template system's design intent (a Jinja2-*inspired* sugar layer over WebComPy's Element/Component system — not a Jinja2-compatible engine) and its intentional limitations are currently split between the spec and a `docs_app` limitations page. This change consolidates all design intent and limitations into the `template-engine` spec as the single source of truth, and removes the `docs_app` page.

## What Changes

- Add a `loop` metadata object to `{% for %}` bodies with the Jinja2 scalar attribute set: `loop.index` (1-based), `loop.index0` (0-based), `loop.revindex`, `loop.revindex0`, `loop.first`, `loop.last`, `loop.length`.
- In static loops and unkeyed `ReactiveList` loops, metadata values are plain values (exact at generation/rebuild time). In keyed `ReactiveDict` loops, metadata values are `Computed`-backed so they stay correct across key-based reconciliation (reorder/add/remove).
- Inside a loop body, `loop` shadows any context variable of the same name (innermost-loop-wins, matching Jinja2).
- Reject known-but-unsupported Jinja2 directives (`{% extends %}`, `{% block %}`, `{% macro %}`, `{% include %}`, `{% set %}`, `{% with %}`, `{% filter %}`, `{% do %}`, `{% trans %}`, `{% autoescape %}`, `{% load %}`, etc.) with a concise `WebComPyException` naming the directive as unsupported. **BREAKING** (behavioral): these previously passed through as literal text.
- Reject unknown `{% word %}` directives with a concise `WebComPyException` ("Unknown template directive"), catching typos like `{% endfo %}`. **BREAKING** (behavioral): unknown directive-like spans previously passed through as literal text. Literal `{%` output remains available via `{% raw %}`.
- Expand the `template-engine` spec's Purpose with the design intent: the template engine is syntactic sugar over the Element/Component system, Jinja2-inspired but explicitly not Jinja2-compatible; composition is done via components and slots, so template inheritance (`extends`/`block`/`macro`/`include`) is a permanent non-goal.
- Rework the four "limitations shall be documented" requirements so the spec is self-contained (no reference to external documentation pages), and update the for-loop limitation requirement to reflect newly-supported loop metadata.
- Remove the `docs_app` limitations page: route entry in `docs_app/router.py`, `docs_app/pages/document/limitations.py`, and `docs_app/templates/document/limitations.py`.

## Capabilities

### New Capabilities

(none — all changes land in the existing `template-engine` capability)

### Modified Capabilities

- `template-engine`: adds requirements for loop metadata in `{% for %}` and for explicit rejection of unsupported/unknown `{% %}` directives; modifies the for-loop limitations requirement; expands the spec Purpose with design intent; makes limitation requirements self-contained.

## Impact

- **Code**: `packages/webcompy/src/webcompy/template/_binder.py` (loop metadata injection), `packages/webcompy/src/webcompy/template/_parser.py` (directive classification), `packages/webcompy/src/webcompy/template/_markdown_for.py` (shared directive classification), `packages/webcompy/src/webcompy/elements/types/_repeat.py` (reactive key-order source for `ReactiveDict` reconciliation).
- **Specs**: `openspec/specs/template-engine/spec.md`.
- **Docs**: removal of `docs_app` limitations page (3 files). No replacement page; the spec becomes the single source of truth.
- **Tests**: new unit tests under `tests/` (loop metadata values, reactive dict metadata updates, directive rejection) and e2e coverage in `e2e/core/`.
- **Breaking behavior**: templates that accidentally contain unsupported/unknown `{% %}` spans will now raise at compile time instead of rendering them as literal text. No valid template (using only supported directives) is affected.

## Known Issues Addressed

- Removes the documented "Loop metadata (`loop.index`, `loop.first`) … NOT supported" limitation from the for-loop semantics requirement.
- Fixes silent pass-through of unsupported/unknown `{% %}` directives, which produced literal garbage output instead of an error.

## Non-goals

- `{% else %}` on `{% for %}`, `break`/`continue`, and `list[tuple]` unpacking remain unsupported (still rejected or documented as limitations).
- Functional loop helpers (`loop.changed()`, `loop.cycle()`, `loop.depth`) are not provided.
- Custom loop-variable naming (Jinja2's fixed `loop` name is kept); `loop` shadowing of context variables inside loop bodies is intentional.
- Full Jinja2 compatibility (template inheritance, macros, includes, whitespace control `{%- -%}`) is explicitly out of scope; unsupported directives are rejected, not emulated.
- No user-facing documentation page replaces the removed `docs_app` limitations page (spec-only consolidation).
