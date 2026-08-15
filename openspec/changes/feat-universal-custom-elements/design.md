# Design: Universal Custom Elements

## Context

`define_component` currently has two forms. The bare form produces an unnamed component whose DOM node IS the template root element (attributes, event handlers, ref, and `:preserve_children` are hoisted onto the component node; a single root element is mandatory). The called form `@define_component("my-card")` produces a named component that renders one custom-element wrapper with the template result as light-DOM children, unlocking multiple roots, `:host` styles, `on_mounted`/`on_unmounted`, and observed attributes. `Component._init_component()` maintains both paths.

Two findings from codebase analysis drive this design:

1. The template engine already assumes the naming convention: `resolve_tag()` converts hyphenated tags via `kebab_to_pascal()` and looks them up in `ComponentStore` by Python function name, and the stdlib HTML parser lowercases tags, so `<user-card>` → `UserCard` is the only working component-reference path in templates. The proposed rule formalizes an existing implicit assumption.
2. `AppDocumentRoot` (`app/_root_component.py`) constructs a `Component` with `generator=None` and relies on the unnamed path because it adopts the existing mount-point node (`#webcompy-app`), which cannot be a custom element. The unnamed path therefore cannot be deleted outright.

Repo migration surface (measured): ~422 bare decorator sites; 299 unique component names of which 34 are single-word (cannot produce a hyphenated name), 2 use acronyms that do not round-trip (`MarkdownSSRPage`, `MarkdownListForSSRPage`), 35 are leading-underscore private test names, and 1 existing named component (`E2ECard`/`e2e-card`) violates the consistency rule. E2E selectors are predominantly `data-testid`-based and survive wrapper insertion.

## Goals / Non-Goals

**Goals:**

- One public component model: every component is a named Light DOM custom element.
- Definition-time enforcement of `func.__name__ == kebab_to_pascal(custom_element_name)` so Python API, template tags, and DOM tags always agree.
- A declarative, type-safe `display` kwarg for the wrapper box, layered over a layout-transparent framework default.
- Silent-failure elimination for transitions on box-less wrappers via a runtime warning.
- Full in-repo migration (tests, e2e, docs_app, CLI templates, demos) in one change.

**Non-Goals:**

- Deleting the internal unnamed path used by `AppDocumentRoot`.
- Deprecation period, per-instance or reactive `display` values, Shadow DOM, `ComponentStore` re-keying (see proposal Non-goals).

## Decisions

### D1: Remove the bare overload; make the name argument required

`define_component` keeps the called form only. The `observed_attributes requires a named custom element` error and all unnamed-rejection branches (`on_mounted`/`on_unmounted` setup rejection in `_component.py`, `:host` rejection in `_css_utils.py`) are deleted. `Component._init_component()` retains the legacy branch but it becomes reachable only through `generator is None`, which only `AppDocumentRoot` uses; add a comment/docstring marking it framework-internal.

*Alternative considered*: refactoring `AppDocumentRoot` off `Component` inheritance to delete the path entirely — rejected as too invasive for no behavioral gain.

### D2: Bidirectional naming check, one direction of normalization

At decoration time, after the existing custom-element-name validation, enforce:

```python
if func.__name__ != kebab_to_pascal(name):
    raise WebComPyComponentException(...)
```

This is equivalent to requiring `name == pascal_to_kebab(func.__name__)` AND that the function name round-trips. Consequences:

- Acronym names are rejected in favor of normalized forms: `HTTPRequest` must be `HttpRequest` (kebab `http-request`). This guarantees template resolution `<http-request>` → `HttpRequest` works.
- Single-word names are rejected implicitly: their derived kebab name lacks a hyphen and fails the existing `_validate_custom_element_name` check. The consistency error message should mention both failure modes with the expected derived name.
- Leading-underscore names fail the custom-element name regex (must start with `[a-z]`).

`pascal_to_kebab` is implemented in `template/_naming.py` next to `kebab_to_pascal`, reusing the regex already present (currently dormant) in `components/_generator.py`: `re_compile("((?<=[a-z0-9])[A-Z]|(?!^)[A-Z](?=[a-z]))")` with `.lower()`. This pattern handles acronym runs (`MyHTTPClient` → `my-http-client`) and digits.

*Alternative considered*: one-directional check (`name == pascal_to_kebab(func.__name__)`) — rejected because it admits names whose template resolution silently fails (`HTTPRequest`/`http-request` resolves to `HttpRequest`).

### D3: `ComponentStore` custom-element-name uniqueness

Add a secondary check in `ComponentStore.add_component` (or at generator registration): a distinct generator whose `custom_element_name` is already claimed by a different generator in the same app raises `WebComPyComponentException`. Rationale: enforced conversion makes `MyHTTPRequest` and `MyHttpRequest` map to the same kebab name while occupying distinct store keys; without this check they would silently share a browser definition via the compatible-reuse path.

### D3b: Deferred registration is per-app (one-time flag enforcement)

The components spec documents `ComponentGenerator.__registered` as a one-time flag: "import-time components will only register into the first app's store." The implementation never sets `_registered`, so import-time components of one app leak into every later app's store in the same process. Enforce the documented semantics with an owning-app record:

- `RenderContext.__init__` provides the app instance via a new `_APP_KEY` DI key alongside `_COMPONENT_STORE_KEY`.
- `ComponentGenerator._try_register()` records `_registered_app` on first successful registration and sets `_registered`. A later context whose app differs skips the import-time generator entirely.
- Later contexts of the SAME app re-register into their fresh per-context store — required because SSR requests and SSG routes each create a new `ComponentStore` and need the full component set.
- Manual DI scopes without `_APP_KEY` (test helpers such as `TestRenderer`) keep the previous always-register behavior, so unit tests are unaffected.
- `LazyComponentGenerator` mirrors `_registered_app` in `_resolve()` so lazy route components behave identically.

*Alternative considered*: global one-time registration with deferred-list pruning — rejected because it would starve later render contexts of the same app (SSG route N+1 would lose scoped styles and template-tag resolution).

### D4: Framework default `display: contents` on wrappers

Inject `[webcompy-component] { display: contents; }` in the earliest practical layer (alongside the framework-level `components` layer rules / the existing `<style id="webcompy-scoped-styles">` mechanism), in both SSR and runtime injection paths. The `webcompy-component` attribute is emitted on every component wrapper, so one attribute selector covers all components without enumerating tag names.

**Implementation decision (resolves the open question below):** the rule lives in a dedicated `<style id="webcompy-component-defaults">` element containing `@layer components { [webcompy-component] { display: contents; } }`, emitted exactly once per document:
- SSR/SSG: prepended to `HeadElement.get_scoped_styles_html()` output, which `webcompy_server/_html.py` inserts *after* the `index.css` link, so the layer-order declaration is the first occurrence of the `components` layer name.
- Browser runtime: created idempotently by `HeadElement._render()` alongside the existing `webcompy-scoped-styles` element, so manual PyScript pages that do not link the framework UI stylesheet still get the rule.
- `components.css` does NOT carry the rule (avoids double emission on pages that link `index.css`).

**Runtime ordering resolution (round-2 review):** `_inject_scoped_style_if_new()` injects cid (`@layer webcompy-scope`) style elements into `<head>` at registration time, i.e. before the first `HeadElement._render()` creates the defaults element. On pages that do NOT link `index.css` (manual PyScript pages, docs demo iframes), cascade-layer priority is fixed by the document-order first occurrence of each layer name, so the framework default would otherwise be declared after `webcompy-scope` and outrank author `:host`/`display` rules. `HeadElement._render()` therefore inserts the defaults element before every existing `style[data-webcompy-cid]`/`style[data-webcompy-cid-rx]` element (appending only when none are present), restoring the `components < webcompy-scope` ordering at runtime. Pages that link `index.css` are unaffected because the fixed `@layer` order statement governs there.

Rationale for `contents` over `block`: `contents` is the only default that does not silently damage authors who did nothing unusual. `block` breaks inline components used in text flow (`<p>…<inline-code>…</p>` splits the paragraph) and changes flex/grid item identity (the wrapper, not the template root, becomes the item) and percentage-size resolution. The `contents` failure modes (`:host` background not painting, transitions not running) only affect authors who opted into wrapper-visible behavior, and both are recoverable: the former is documented, the latter gets a runtime warning (D7). Historical `display: contents` accessibility-tree bugs are fixed in modern browsers.

*Alternatives considered*: `block` default (rejected above); no framework rule (browser default `inline` causes anonymous-box splitting around block children — worst option).

### D5: `display` kwarg with Literal + get_args + TypeGuard

```python
ComponentDisplay: TypeAlias = Literal[
    "contents", "block", "inline", "inline-block",
    "flex", "inline-flex", "grid", "inline-grid", "flow-root",
]

_VALID_DISPLAY_VALUES: Final = frozenset(get_args(ComponentDisplay))

def _is_component_display(value: str) -> TypeGuard[ComponentDisplay]:
    return value in _VALID_DISPLAY_VALUES
```

- `ComponentDisplay` is exported from `webcompy.components` for IDE completion.
- `define_component(..., display: ComponentDisplay | None = None)`: statically strict for pyright users; the runtime guard narrows to `ComponentDisplay` before the value reaches `ComponentGenerator.__init__`, so unverified strings cannot flow in at the type level. The error message lists valid values derived from the same `Literal`, keeping type, validation, and message in one source of truth.
- `none` is deliberately excluded: invisibility is a scoped-style concern, not a wrapper-layout concern.

**Emission and precedence** — implemented by prepending one rule to the existing cid style pipeline:

```
priority (weak → strong):
① [webcompy-component] { display: contents }        framework layer (early)
② my-card[webcompy-cid-x] { display: block }        from kwarg; first rule in the
                                                    component's @layer webcompy-scope style
③ my-card[webcompy-cid-x] { display: flex }         author's :host scoped style
                                                    (same layer/specificity, later → wins)
```

② rides the existing `scoped_style` getter (`_render_scoped_style_css` host_tag path), so SSR `<style data-webcompy-cid>`, runtime injection, and SSG all pick it up with no new injection path. ② must use the cid-scoped selector, not a bare `my-card` element selector, because the attribute selector (0,1,0) would otherwise out-specificity it against ① (also 0,1,0 but earlier layer — actually ① sits in an earlier layer so ② wins regardless; cid scoping keeps ② vs ③ ordering deterministic by source order at equal specificity).

### D6: Multi-root and fragment results become universal

`_normalize_component_template()` becomes the only setup-result path. Returning a `FragmentElement` (e.g., multi-root `render_markdown` output) is legal as a single child, inverting the current `Root Node of Component must be instance of 'Element'` behavior for public components. The `AppDocumentRoot` internal path keeps its single-root assumption.

### D7: Transition display warning

In `Transition._resolve_duration()`, where computed style is already read, additionally read `display`; if it is `contents` or `none`, log a warning naming the transition and advising `display="block"` (or another box-generating value) on the child component. Transitions on box-less elements resolve duration normally but `transitionend`/`animationend` never fire; the existing timeout fallback finalizes the sequence, so the failure mode today is a silent delay with no animation. The warning converts it into a diagnosable message.

### D8: Big-bang in-repo migration with a rename map

No deprecation window (per project decision). Migration order: rename map first (all 299 names, checked for intra-app collisions, e.g. docs_app `Home` cannot become `HomePage` because that name is taken; tests' `_Page` cannot become `Page` because it is single-word), then framework, then call sites. `lazy()` import paths are runtime strings (`"module:Attribute"`) invisible to pyright — update by grep and verify by exercising every route in tests/e2e. Tag names stay stable where the Python name already round-trips (`E2ECard` → `E2eCard` keeps `e2e-card`; its e2e selectors are untouched).

## Risks / Trade-offs

- [Structural pseudo-classes and sibling combinators in user scoped styles change meaning (`:first-child` on a component root is now always true; `.a + .b` across sibling components breaks)] → Migration guide section; repo scan confirmed no such usage in docs_app/e2e.
- [Extra DOM node per component deepens trees and adds `customElements.define` calls at startup] → Acceptable: registration is idempotent and per-component cost is one call; node accounting (`_node_count == 1`) is unchanged.
- [`display: contents` wrapper yields zero-size `getBoundingClientRect` and no `:host` paint, surprising authors who style the wrapper] → Docs establish the idiom "declare `display` when styling the wrapper"; kwarg makes it one line.
- [`lazy()` string references missed during renames fail only at navigation time] → Grep-based update + full route traversal in e2e; add a tasks item to audit all `lazy(` call sites.
- [Renames change cids (`generate_id` is name-derived), shifting SSR `data-webcompy-cid` values and scoped-style selectors] → Tests reference cids dynamically; SSR and client rename together so hydration stays consistent.
- [Two apps in one document silently share a custom-element definition when names collide with matching metadata] → Pre-existing compatible-reuse semantics; naming rule makes collisions semantically meaningful; documented in custom-elements doc.
- [Browser-level constraint: page-global registry means `font-face` etc. remain reserved] → Existing reserved-name validation unchanged.

## Migration Plan

1. Framework core (D1–D7) with unit tests updated in lockstep.
2. Rename map + mechanical migration of tests/, e2e/, docs_app/, CLI template_data/, demos.
3. Docs rewrite (`custom_elements.md`, quickstart samples) + migration guide for downstream users.
4. Full verification: ruff, pyright, pytest, `webcompy generate`, all e2e groups.

Rollback: revert the change; no data or persisted-state migration is involved (SSR/client consistency is per-build).

## Open Questions

- ~~Exact home for the framework default rule (`components.css` vs the `webcompy-scoped-styles` style element) — decide at implementation; both satisfy the layering requirement.~~ Resolved in D4: a dedicated `webcompy-component-defaults` style element emitted with the scoped-styles output and at runtime; `components.css` does not carry the rule.
- Whether `display` kwarg rules should also be emitted for the server when no other scoped style exists (lean: emit only when set — trivially satisfied by the pipeline).
