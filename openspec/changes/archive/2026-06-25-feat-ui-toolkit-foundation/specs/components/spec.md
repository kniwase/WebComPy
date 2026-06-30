# Components

## ADDED Requirements

### Requirement: Scoped CSS SHALL be wrapped in `@layer webcompy-scope` automatically

When the framework emits a `<style data-webcompy-cid="{hash}">` element for a component's `scoped_style`, the framework SHALL wrap the rule body in `@layer webcompy-scope { ... }`. This applies to both server-side rendered output and client-side runtime injection. The wrapping is automatic and does not require opt-in by the developer.

#### Scenario: SSR output wraps scoped_style in @layer

- **WHEN** a component's `scoped_style = {".btn": {"color": "red"}}` is rendered during SSR
- **THEN** the server-rendered `<style data-webcompy-cid="...">` element SHALL contain `@layer webcompy-scope { .btn[webcompy-cid-xxx] { color: red; } }`
- **AND** the rule SHALL have lower priority than unlayered rules in the same stylesheet

#### Scenario: Runtime injection wraps scoped_style in @layer

- **WHEN** a component's `scoped_style` is injected at browser runtime (no SSR)
- **THEN** the runtime-injected `<style data-webcompy-cid="...">` element SHALL contain the same `@layer webcompy-scope { ... }` wrapper
- **AND** the visual result SHALL match the SSR case

#### Scenario: A components.css rule overrides a scoped_style rule

- **WHEN** the framework's `components.css` defines a rule for a selector that also appears in a component's `scoped_style`
- **AND** `components.css` is declared in the `components` layer, declared before `webcompy-scope`
- **THEN** the `components.css` rule SHALL win over the `scoped_style` rule

## MODIFIED Requirements

### Requirement: Scoped CSS SHALL be injected at browser runtime when SSR is absent

The framework SHALL inject scoped component styles as per-component `<style data-webcompy-cid="{hash}">` elements in `document.head`, along with a single `<style id="webcompy-scoped-styles">` element for the framework-level `*[hidden]{display:none}` rule. Style injection SHALL be idempotent: before creating any `<style>` element, the framework SHALL check for an existing element with the same identifier (`data-webcompy-cid` or `id`). When SSR has already produced these elements, the runtime SHALL detect them and skip injection. New components registered after initial render (e.g., lazy-loaded routes) SHALL have their styles injected on the next render cycle. Each injected `<style data-webcompy-cid>` element SHALL contain its rules wrapped in `@layer webcompy-scope { ... }`.

#### Scenario: Runtime injection when SSR is absent

- **WHEN** a `WebComPyApp` is created and `app.run()` is called at browser runtime with no pre-existing `<style id="webcompy-scoped-styles">` or `<style data-webcompy-cid="...">` elements in the DOM
- **THEN** `AppDocumentRoot._render()` SHALL create a `<style id="webcompy-scoped-styles">` element with `*[hidden]{display:none}`
- **AND** SHALL create a `<style data-webcompy-cid="...">` element for each registered component that has `scoped_style`, with rules wrapped in `@layer webcompy-scope`
- **AND** SHALL append all style elements to `document.head`
- **AND** component `scoped_style` rules SHALL apply correctly

#### Scenario: No duplicate when SSR has already injected styles

- **WHEN** a `WebComPyApp` hydrates a page that was server-side rendered
- **AND** the SSR output already contains both `<style id="webcompy-scoped-styles">` and `<style data-webcompy-cid="...">` elements in the document head
- **THEN** `_reconcile_scoped_styles()` SHALL check for existing elements via `querySelector`
- **AND** finding existing elements, SHALL skip injection for each
- **AND** no duplicate `<style>` elements SHALL be created

#### Scenario: Runtime style injection in isolated contexts

- **WHEN** a `WebComPyApp` runs inside an iframe with no SSR
- **THEN** scoped component styles SHALL be injected at runtime as per-component `<style>` elements, each wrapped in `@layer webcompy-scope`
- **AND** components inside the iframe SHALL render with their defined `scoped_style` CSS

## REMOVED Requirements

(none)
