# Spec Delta

## MODIFIED Requirements

### Requirement: SSR/SSG output SHALL emit layered scoped style elements after the layer-order declaration

In SSR/SSG-generated HTML, all `<style data-webcompy-cid="...">` and `<style data-webcompy-cid-rx="...">` elements (which contain rules layered via `@layer webcompy-scope`) SHALL be emitted after the stylesheet link that declares the fixed layer order (`/_webcompy-ui/index.css`, optionally carrying a `?v=<hash>` cache-busting query string). This ensures the declaration `@layer reset, tokens, components, prose, webcompy-scope;` is the first occurrence of each layer name in document order, per CSS Cascade 5 §6.4.3, so the intended cascade priority holds in SSR output exactly as it does in CSR output.

#### Scenario: Scoped styles follow the index.css link in generated HTML

- **WHEN** an SSR/SSG page is generated for an app whose components define `scoped_style`
- **THEN** in the generated `<head>`, every `<style data-webcompy-cid="...">` and `<style data-webcompy-cid-rx="...">` element SHALL appear after the `<link rel="stylesheet" href=".../_webcompy-ui/index.css">` element (including when a `?v=<hash>` query string is present)
- **AND** the effective cascade layer order SHALL be `reset < tokens < components < prose < webcompy-scope` (lowest to highest priority)

#### Scenario: App without prose.css still gets the full layer order

- **WHEN** an SSR/SSG page is generated for an app that does not link `prose.css`
- **THEN** the layer-order declaration in `index.css` (which lists all five layers including `prose`) SHALL still precede all layered rules
- **AND** scoped styles SHALL retain the highest layered priority
