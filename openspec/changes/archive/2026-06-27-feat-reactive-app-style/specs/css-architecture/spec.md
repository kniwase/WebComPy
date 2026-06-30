# CSS Architecture Delta

## ADDED Requirements

### Requirement: Framework cascade shall include webcompy-dynamic

The framework's CSS cascade SHALL be declared in `webcompy/ui/_styles/index.css` as:

```css
@layer reset, tokens, components, webcompy-scope, webcompy-dynamic;
```

The `webcompy-dynamic` layer SHALL be the highest-priority layer in the cascade. Dynamic styles registered via `app.append_style` SHALL be wrapped in this layer.

#### Scenario: index.css declares the full cascade
- **WHEN** the framework CSS is loaded
- **THEN** `index.css` SHALL declare `@layer reset, tokens, components, webcompy-scope, webcompy-dynamic;`
- **AND** this declaration SHALL appear before any rule in any other framework CSS file

#### Scenario: Dynamic style elements are wrapped in webcompy-dynamic
- **WHEN** `app.append_style(":root { --x: red; }")` is called
- **THEN** the rendered `<style data-webcompy-dynamic>` element's textContent SHALL start with `@layer webcompy-dynamic {`
- **AND** it SHALL end with `}`
