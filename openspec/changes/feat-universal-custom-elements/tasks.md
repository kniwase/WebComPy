# Tasks: Universal Custom Elements

## 1. Framework Core — Naming and Definition API

- [x] 1.1 Add `pascal_to_kebab` to `packages/webcompy/src/webcompy/template/_naming.py` next to `kebab_to_pascal` (reuse the camel-to-kebab regex from `components/_generator.py`, handling acronym runs and digits); export it and add doctests/unit tests including `MyCard → my-card`, `ToDoListPage → to-do-list-page`, `E2ECard → e2-e-card`, `MarkdownSSRPage → markdown-ssr-page`
- [x] 1.2 Remove the bare `@define_component` overload in `components/_generator.py`; make the custom-element name the required first positional argument; update the signature, docstrings, and `__init__.py` exports
- [x] 1.3 Implement the bidirectional naming-consistency check in `define_component`: after `_validate_custom_element_name`, raise `WebComPyComponentException` unless `func.__name__ == kebab_to_pascal(name)`, with a message showing function name, declared name, and expected name (guiding acronym renames like `HTTPRequest` → `HttpRequest` and single-word renames like `App`)
- [x] 1.4 Add the `ComponentDisplay` `Literal` alias, `_VALID_DISPLAY_VALUES` frozenset via `get_args`, and the `_is_component_display` `TypeGuard` helper in `components/_generator.py`; export `ComponentDisplay` from `webcompy.components`
- [x] 1.5 Add the keyword-only `display: ComponentDisplay | None = None` argument to `define_component`, validate via the TypeGuard (raising `WebComPyComponentException` listing valid values from the alias), and thread the narrowed value through `ComponentGenerator.__init__` into a `_display` attribute; mirror the attribute in `LazyComponentGenerator._resolve`
- [x] 1.6 Emit the display kwarg rule in `ComponentGenerator.scoped_style`: prepend `{custom-element-name}[webcompy-cid-{cid}] { display: <value>; }` before author rules when `_display` is set (verify SSR `<style data-webcompy-cid>` and runtime injection paths both include it)
- [x] 1.7 Add custom-element-name uniqueness enforcement to `ComponentStore.add_component` (reject a distinct generator claiming an already-claimed custom-element name with `WebComPyComponentException`)

## 2. Framework Core — Component Internals

- [x] 2.1 In `components/_component.py`, mark the `generator is None` branch of `_init_component` as framework-internal (`AppDocumentRoot` only) with a comment; remove the unnamed-rejection branches for `on_mounted`/`on_unmounted` (both the sync setup path and `_refresh_async_setup_results`) since public unnamed components no longer exist
- [x] 2.2 Remove the `:host`-without-named-element rejection in `components/_css_utils.py` (`_resolve_host_part`) and the `host_tag=None` fallback paths in `_css_utils.py`/`_libs.py`, since every public generator now has a custom-element name
- [x] 2.3 Remove the `observed_attributes requires a named custom element` error path in `define_component`
- [x] 2.4 Delete the now-dormant `_camel_to_kebab_pattern` from `components/_generator.py` if it was moved to `_naming.py` in 1.1
- [x] 2.5 Verify `_normalize_component_template` is the only setup-result path for public components (single root, list/tuple, text, signal, `None`, and `FragmentElement` results all render inside the wrapper)

## 3. Framework Core — Styles and Transition Warning

- [x] 3.1 Add the framework-default rule `[webcompy-component] { display: contents; }` in an early cascade layer, emitted once per document in both SSR output and runtime injection (per design D4: dedicated `<style id="webcompy-component-defaults">` element prepended to `get_scoped_styles_html()` and created idempotently by `HeadElement._render()`; `components.css` does not carry the rule); verify precedence: default < display kwarg < author `:host` scoped style
- [x] 3.2 In `elements/types/_transition.py` `_resolve_duration`, when duration resolves from computed styles, also read computed `display`; if `contents` or `none`, log a warning naming the transition and advising a box-generating display (e.g., `display="block"` on the child component); keep timeout fallback behavior unchanged
- [x] 3.3 Migrate the framework-internal `packages/webcompy/src/webcompy/ui/code_block/_component.py` to `@define_component("code-block")` and verify the markdown `code_blocks=True` integration

## 4. Unit Tests — Framework Behavior

- [x] 4.1 Add tests for the naming-consistency check: consistent pair accepted; mismatched name rejected; acronym name rejected with guidance; single-word name rejected; reserved names still rejected
- [x] 4.2 Add tests for the `display` kwarg: valid values accepted and emitted (SSR + runtime), invalid value raises with the alias-derived list, `:host` scoped style overrides the kwarg rule
- [x] 4.3 Add tests for `ComponentStore` custom-element-name collision (`MyHTTPRequest` vs `MyHttpRequest` style pairs)
- [x] 4.4 Update or remove tests asserting removed behaviors: bare-form definitions, `Root Node of Component must be instance of 'Element'` for multi-root/fragment results, unnamed `on_mounted`/`on_unmounted` rejection, unnamed `:host` rejection, `observed_attributes` without name rejection
- [ ] 4.5 Add a test for the Transition display warning (contents/none child logs warning, sequence still finalizes via timeout)
- [x] 4.6 Rework `tests/test_custom_element_components.py` for the naming rule (e.g., `my-card`/`Card` → `MyCard`, `e2e-card`/`Card` pairs, `inner-card`/`Inner` → `InnerCard`, `my-card-2`/`NonRenderable` removal or rename)

## 5. Repo Migration — Rename Map and Test Suite

- [x] 5.1 Produce the full rename map for all ~299 in-repo component names (34 single-word, 2 acronym, 35 underscore-prefixed, plus `E2ECard`); check intra-app collisions (e.g., docs_app `Home` cannot become `HomePage`; tests `_Page` needs a multi-word replacement); record the map in the change directory for reviewers
- [x] 5.2 Migrate `tests/` bare decorator sites to named form (mechanical: `@define_component` → `@define_component("<derived-name>")`, applying renames from the map including underscore-prefixed test components)
- [x] 5.3 Update exact-HTML and cid-sensitive assertions in `tests/` for wrapper insertion and rename-derived cid changes
- [x] 5.4 Run `uv run python -m pytest tests/ --tb=short` until green

## 6. Repo Migration — E2E, docs_app, CLI Templates, Demos

- [x] 6.1 Migrate `e2e/core/my_app/` pages (including `E2ECard` → `E2eCard` keeping tag `e2e-card`); audit all `lazy(` import-path strings; run `scripts/run-e2e-tests.sh` per group until green
- [x] 6.2 Migrate `docs_app/` components and pages, including renaming the `ui.py` kit (`Button`/`Card`/`Link`/`Section` collide with native element names — pick multi-word replacements such as `DocsButton`/`DocsCard`) and updating `docs_manifest.py`/`router.py` lazy references
- [x] 6.3 Migrate `packages/webcompy-cli/src/webcompy_cli/template_data/` scaffold components (`Root`, `Navigation`, `Input`, `Home`, `Fizzbuzz`, `NotFound` — all single-word, need multi-word renames) including route config and any lazy strings
- [x] 6.4 Migrate `docs_app/static/_demos/` apps (seven `App` components → multi-word names) and verify demo pages still render via the inspect CLI

## 7. Documentation and Final Verification

- [ ] 7.1 Rewrite `docs_app/documents/custom_elements.md`: named-only model, naming-consistency rule with rename guidance, layout-transparent default + `display` kwarg idiom, updated multiple-roots/hooks/observed-attributes sections
- [ ] 7.2 Update `quickstart.md`, `installation.md`, `README.md`/`README.ja.md`, and other docs samples using bare `@define_component` (including the `_css_template.py` docstring example); add a migration-guide section covering structural pseudo-class/sibling-combinator meaning changes, Transition + `display` requirement, and `lazy()` string updates
- [ ] 7.3 Update `AGENTS.md` (File → Spec Mapping and Framework Invariants if wording needs it) and run `python3 scripts/check-doc-spec-refs.py`
- [ ] 7.4 Full local CI: `uv run ruff check .`, `uv run ruff format --check .`, `uv run pyright`, `uv run python -m pytest tests/ --tb=short`, `uv run python -m webcompy generate`, `scripts/run-e2e-tests.sh`; run `openspec validate feat-universal-custom-elements`

## 8. Review-fix hardening (post-review)

- [x] 8.1 Inject the wrapper `display: contents` default at browser runtime via `HeadElement._render()` and in SSR via `get_scoped_styles_html()` (dedicated `webcompy-component-defaults` element, exactly once per document); remove the rule from `components.css`; add SSR/runtime emission tests
- [x] 8.2 Enforce per-app deferred component registration per design D3b: `_APP_KEY` DI key + `_registered_app` record in `_try_register()`; same-app later contexts re-register, other apps skip; lazy generators mirror the record; add cross-app and same-app multi-context tests
- [x] 8.3 Harden the `display` kwarg validation: reject non-string/unhashable values with `WebComPyComponentException` and list valid values in declared `ComponentDisplay` order
- [ ] 8.4 Add component-wrapper Transition coverage: unit tests with real component children and E2E cases for the default layout-transparent wrapper (warn + timeout finalize) vs `display="block"` (animates, no warning)

## 9. Review-fix hardening (round 2)

- [x] 9.1 Fix runtime head ordering of the wrapper display default in `HeadElement._render()`: position the `webcompy-component-defaults` style element before every existing `style[data-webcompy-cid]` / `style[data-webcompy-cid-rx]` element (fall back to append when none), so `@layer components` is a document-order first occurrence before `@layer webcompy-scope` even on pages without the framework UI stylesheet; add unit tests covering the pre-seeded-cid, cid-rx, append-only, and multi-render cases
- [x] 9.2 Remove the now-dead `custom_element_name is not None` guard in `ComponentStore.add_component` (the type is `str` and can no longer be `None`)
- [x] 9.3 Extend the `custom-element-components` delta spec with the runtime ordering requirement and scenario; note the decision in `design.md` D4

## 10. Review-fix hardening (round 3)

- [x] 10.1 Fix `LazyComponentGenerator.display` to resolve lazily like `custom_element_name`: remove the `_display = None` initialization so the property falls back to `__getattr__` -> `_resolve()` instead of silently returning `None` before resolution; add a unit test asserting `display` resolves to the component's value and triggers resolution
- [ ] 10.2 Remove the unused `wrapper_display` parameter and tuple return from the `_component_toggle_root` test helper in `tests/test_transition.py`
