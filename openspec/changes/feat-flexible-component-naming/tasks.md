# Tasks: Flexible Component Naming

## 1. Core decorator implementation

- [x] 1.1 Change `define_component` signature in `packages/webcompy/src/webcompy/components/_generator.py` to `custom_element_name: str | None = None` (positional-or-keyword) with existing keyword-only args; keep factory-call validation of explicit tag, observed_attributes, display; add an eager bare-application guard raising when the first argument is callable (guidance to call the decorator factory), plus an isinstance guard against decorating a `ComponentGenerator`
- [x] 1.2 Move tag resolution into the returned decorator: derive `pascal_to_kebab(component_def.__name__)` when the argument is omitted, validate derived result via `_validate_custom_element_name` with rename-or-explicit-tag guidance, and pass the resolved tag into `_create_generator`
- [x] 1.3 Add re-decoration guard raising `WebComPyComponentException` when the decorated object already carries `__webcompy_component_definition__`; remove the name-mismatch block (expected-name check and derived-suggestion logic)
- [x] 1.4 Update `define_component` docstring (Google style, no OpenSpec references) for the new call forms; update `.pyi` stub if one exists
- [x] 1.5 Run `uv run pyright packages/webcompy` and `uv run ruff check packages/webcompy`

## 2. Unit tests

- [x] 2.1 Add tests for derivation success (`UserCard` → `user-card`), keyword form (`custom_element_name=`), and non-round-tripping acronym acceptance (`HTTPRequest` → `http-request`)
- [x] 2.2 Add tests for the derived-failure error catalog: hyphen-less (`App`), reserved (`FontFace`), regex-invalid (`my_card`) — asserting guidance mentions rename or explicit tag
- [x] 2.3 Add tests for explicit-tag freedom (`Card` + `"user-card"` succeeds), invalid explicit tags still rejected, and re-decoration guard raising
- [x] 2.4 Add a test that applying `define_component` bare (undecorated contract) does not produce a usable generator under the new API (documents D4 #7)
- [x] 2.5 Run `uv run python -m pytest tests/ --tb=short` and fix fallout

## 3. Codebase sweep — pattern A (derivable names → omitted form)

- [x] 3.1 Convert framework component definitions to the called/omitted form where names derive (`packages/webcompy/src/webcompy/ui/code_block/_component.py`, docstring examples inside framework modules such as `_reactive_scoped_style.py`, `_css_template.py`)
- [x] 3.2 Convert docs_app definitions (`components/`, `layout/`, `templates/`, `pages/`) that match pattern A to `@define_component()` or kwargs-only form
- [x] 3.3 Convert CLI scaffold templates (`packages/webcompy-cli/src/webcompy_cli/template_data/app/components/*.py`) to pattern A form; verify `webcompy init` output compiles
- [x] 3.4 Mechanically convert unit-test definitions whose names round-trip to the omitted form across `tests/` (full conversion per proposal); re-run full pytest
- [x] 3.5 Convert E2E corpus app definitions (`e2e/core/my_app/**`, `loading_app`, `profile_app`) whose names round-trip to the omitted form

## 4. Codebase sweep — pattern B (rename verbose functions, tags unchanged)

- [x] 4.1 Rename demo app functions keeping explicit tags: `HelloWorldApp`→`HelloWorld`, `FetchSampleApp`→`FetchSample`, `MatplotlibSampleApp`→`MatplotlibSample`, `TeleportDemoApp`→`TeleportDemo`, `TransitionDemoApp`→`TransitionDemo` in `docs_app/static/_demos/*/app.py`
- [x] 4.2 Update all references to renamed functions within each demo module (route tables, templates); confirm no external imports exist
- [x] 4.3 Finalize list scan for any remaining doubled-qualifier names matching pattern B criteria; apply same treatment or record as intentional `-page` suffixes

## 5. Specs and documentation sync

- [x] 5.1 Update live-spec examples using the bare undecorated form to the called form (`openspec/specs/reactive-scoped-style/spec.md`, plus any other live spec instances found by grep excluding archive)
- [x] 5.2 Rewrite naming-rules section of `docs_app/documents/custom_elements.md`: optional argument, derivation rules, acronym acceptance, updated migration section from the old bare era, examples covering both paths
- [x] 5.3 Update `docs_app/documents/quickstart.md` examples to preferred forms
- [x] 5.4 Grep `docs_app/documents/` and `docs_app/` non-generated code for stale claims about mandatory name matching; fix all hits

## 6. Verification

- [ ] 6.1 Run full local CI subset: `uv run ruff check . && uv run ruff format --check . && uv run pyright`
- [ ] 6.2 Run `uv run python -m pytest tests/ --tb=short --cov=webcompy`
- [ ] 6.3 Run `uv run python -m webcompy generate` on docs_app successfully
- [ ] 6.4 Run E2E groups exercising swept code: `scripts/run-e2e-tests.sh components` and `scripts/run-e2e-tests.sh docs-home` (plus custom-elements-related group if present)
- [ ] 6.5 Verify browser behavior manually if feasible via `uv run python -m webcompy inspect verify` on a page using a derived-form component (registration/hydration unaffected)
