## ADDED Requirements

### Requirement: Scoped style shall support nested dictionary structures for media queries and pseudo-selectors
The framework SHALL allow developers to define nested style dictionaries within `scoped_style`, where nested keys represent `@media` queries, `@supports` rules, or pseudo-class selectors. The framework SHALL recursively process these nested structures and generate valid CSS rules with proper selector scoping.

#### Scenario: Defining a media query within scoped style
- **WHEN** a developer sets `scoped_style` with a nested `@media` rule:
  ```python
  {".button": {"color": "blue", "@media (max-width: 768px)": {"color": "red"}}}
  ```
- **THEN** the framework SHALL generate two CSS rules:
  ```css
  .button[webcompy-cid-xxx] { color: blue; }
  .button[webcompy-cid-xxx] @media (max-width: 768px) { color: red; }
  ```
- **AND** both rules SHALL be scoped to the component via the `[webcompy-cid-xxx]` attribute

#### Scenario: Defining a pseudo-class selector within scoped style
- **WHEN** a developer sets `scoped_style` with a nested pseudo-class:
  ```python
  {".button": {"color": "blue", ":hover": {"background": "yellow"}}}
  ```
- **THEN** the framework SHALL generate:
  ```css
  .button[webcompy-cid-xxx] { color: blue; }
  .button[webcompy-cid-xxx] :hover { background: yellow; }
  ```

#### Scenario: Defining deeply nested structures
- **WHEN** a developer defines multiple levels of nesting:
  ```python
  {".button": {
      "color": "blue",
      "@media (max-width: 768px)": {
          "color": "red",
          ":hover": {"background": "yellow"}
      }
  }}
  ```
- **THEN** the framework SHALL generate:
  ```css
  .button[webcompy-cid-xxx] { color: blue; }
  .button[webcompy-cid-xxx] @media (max-width: 768px) { color: red; }
  .button[webcompy-cid-xxx] @media (max-width: 768px) :hover { background: yellow; }
  ```

#### Scenario: Multiple selectors with nested structures
- **WHEN** a developer defines nested styles for multiple selectors:
  ```python
  {
      ".button": {"color": "blue", "@media (max-width: 768px)": {"color": "red"}},
      ".link": {"text-decoration": "none", ":hover": {"text-decoration": "underline"}}
  }
  ```
- **THEN** the framework SHALL generate valid CSS for all selectors with proper scoping
- **AND** each component's styles SHALL remain isolated to that component

### Requirement: Nested scoped style shall maintain type safety with recursive type definition
The framework SHALL provide type annotations that accurately describe the nested structure of scoped styles, enabling IDE autocomplete and static type checking.

#### Scenario: Type checking nested style definitions
- **WHEN** a developer defines nested styles with incorrect types (e.g., a number instead of string for a CSS value)
- **THEN** a type checker (Pyright/MyPy) SHALL report a type error
- **AND** valid nested structures SHALL pass type checking without errors

#### Scenario: Backward compatibility with flat style definitions
- **WHEN** a developer uses the existing flat style structure:
  ```python
  {".button": {"color": "blue"}}
  ```
- **THEN** the code SHALL pass type checking without errors
- **AND** the generated CSS SHALL be identical to the current behavior

### Requirement: Nested scoped style shall support all CSS at-rules and pseudo-selectors
The framework SHALL accept any string key in nested style dictionaries, allowing developers to use `@media`, `@supports`, `@container`, pseudo-classes (`:hover`, `:focus`, `:active`), and pseudo-elements (`::before`, `::after`).

#### Scenario: Using @supports rule
- **WHEN** a developer defines:
  ```python
  {".card": {"padding": "20px", "@supports (display: grid)": {"display": "grid"}}}
  ```
- **THEN** the framework SHALL generate:
  ```css
  .card[webcompy-cid-xxx] { padding: 20px; }
  .card[webcompy-cid-xxx] @supports (display: grid) { display: grid; }
  ```

#### Scenario: Using pseudo-elements
- **WHEN** a developer defines:
  ```python
  {".tooltip": {"position": "relative", "::after": {"content": "attr(data-tip)"}}
  ```
- **THEN** the framework SHALL generate:
  ```css
  .tooltip[webcompy-cid-xxx] { position: relative; }
  .tooltip[webcompy-cid-xxx] ::after { content: attr(data-tip); }
  ```

#### Scenario: Using combinator selectors in nested structure
- **WHEN** a developer defines:
  ```python
  {".menu": {"color": "black", "> li": {"color": "blue"}}}
  ```
- **THEN** the framework SHALL generate:
  ```css
  .menu[webcompy-cid-xxx] { color: black; }
  .menu[webcompy-cid-xxx] > li { color: blue; }
  ```
