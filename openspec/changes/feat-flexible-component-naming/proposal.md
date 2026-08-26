# Proposal: Flexible Component Naming

## Why

`define_component` currently forces the setup function name to equal `kebab_to_pascal(custom_element_name)`. This couples two independent identifiers: the Python function name and the custom-element tag. The coupling produces unnatural component names (e.g., `HelloWorldApp` only to satisfy the tag `hello-world-app`), blocks legitimate names such as `HTTPRequest` (non-round-tripping acronyms), and makes the bare-but-called form `@define_component()` impossible even when the tag can be trivially derived from the function name.

## What Changes

- `define_component` SHALL always be called (`@define_component(...)`); the first positional-or-keyword argument becomes `custom_element_name: str | None = None` (previously required positional `name`).
  - **BREAKING (edge case only):** the previously rejected bare form now raises a clear error instructing to call the decorator; existing called forms are source-compatible.
- When `custom_element_name` is omitted, the tag SHALL be derived as `pascal_to_kebab(function.__name__)`; only the derived result is validated against custom-element naming rules (lowercase, contains hyphen, not reserved). The round-trip check (`kebab_to_pascal(derived) == function.__name__`) is removed, so non-round-tripping names like `HTTPRequest` → `<http-request>` become valid.
- When `custom_element_name` is provided explicitly, the framework SHALL NOT compare it against the setup function name; the mismatch-detection requirement is removed. The explicit value itself keeps full naming-rule validation.
- Existing codebase sweep so the new forms are exercised end to end:
  - Definitions whose function name already matches the derivation switch to the omitted form `@define_component()` or keyword-only kwargs.
  - Verbose function names that existed only to mirror their tags (e.g., `HelloWorldApp`, `FetchSampleApp`, demo apps with doubled qualifiers) are renamed to simpler names while keeping the explicit tags unchanged.
  - Lifecycle-independent unit tests convert matching definitions to the omitted/derived form so the whole test suite exercises the new path by default.
- Documentation and live specs that describe or exemplify the removed behaviors are updated (`docs_app/documents/custom_elements.md`, `docs_app/documents/quickstart.md`, spec examples using the bare undecorated form).
- CLI scaffold templates (`webcompy_cli/template_data`) migrate to the omitted form where names already derive.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `components`: the naming-consistency requirement is rewritten — `define_component` gains an optional `custom_element_name` argument with derivation semantics, the mandatory name-match validation is removed, error scenarios are replaced with derived-name failure modes and a re-decoration guard.
- `custom-element-components`: the named-component definition requirement no longer requires the element name to match the setup function name via case conversion; both explicit and derived naming paths are specified.
- `async-component-setup`: examples and requirements referencing the bare `@define_component` decorator form are updated to the always-called form, since the bare form remains unsupported under the new API.

## Impact

- **Framework code**: `packages/webcompy/src/webcompy/components/_generator.py` (`define_component`, `_create_generator`, `_validate_custom_element_name` usage), docstring updates; `packages/webcompy/src/webcompy/components/__init__.pyi` if present.
- **Definitions**: `packages/webcompy/src/webcompy/ui/code_block/_component.py`, all `docs_app/components|layout|templates|pages`, `docs_app/static/_demos/*/app.py`.
- **CLI scaffold**: `packages/webcompy-cli/src/webcompy_cli/template_data/app/components/*.py`.
- **Tests**: `tests/**` definitions converted to the derived form where applicable plus new tests for derivation, explicit-naming freedom, and error catalog.
- **Docs site pages**: `docs_app/documents/custom_elements.md`, `quickstart.md`.
- **Live specs**: three delta files under this change; no runtime behavior outside the decorator itself changes.

## Known Issues Addressed

None of the tracked known issues (signal system, element system, router, general) are addressed by this change; the component-system item "Component IDs are MD5 hashes" remains open and unrelated.

## Non-goals

- No support for the undecorated callable form `@define_component` used directly as a decorator; the decorator MUST be called.
- No prop-to-attribute reflection or attribute→prop type coercion changes.
- No changes to custom-element registration/hydration behavior, observed-attribute normalization rules, or reserved-name lists.
- No virtual-DOM diffing or ID-generation changes.
