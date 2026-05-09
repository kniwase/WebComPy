## MODIFIED Requirements

### Requirement: Scoped CSS shall support nested dictionary structures for media queries and pseudo-selectors
The framework SHALL allow developers to define nested style dictionaries within `scoped_style`, where nested keys represent `@media` queries, `@supports` rules, or pseudo-class selectors. The framework SHALL recursively process these nested structures and generate valid CSS rules with proper selector scoping. At-rules (`@media`, `@supports`, `@container`) SHALL wrap selectors inside their blocks. Pseudo-classes (`:hover`, `:focus`) and pseudo-elements (`::before`, `::after`) SHALL attach directly to selectors without space. Combinator selectors (`>`, `+`, `~`, descendant space) SHALL maintain space separation.

#### Scenario: Defining a media query within scoped style
- **WHEN** a developer sets `scoped_style` with a nested `@media` rule:
  ```python
  {".button": {"color": "blue", "@media (max-width: 768px)": {"color": "red"}}}
  ```
- **THEN** the framework SHALL generate valid CSS with at-rule wrapping:
  ```css
  .button[webcompy-cid-xxx] { color: blue; }
  @media (max-width: 768px) { .button[webcompy-cid-xxx] { color: red; } }
  ```
- **AND** both rules SHALL be scoped to the component via the `[webcompy-cid-xxx]` attribute

#### Scenario: Defining a pseudo-class selector within scoped style
- **WHEN** a developer sets `scoped_style` with a nested pseudo-class:
  ```python
  {".button": {"color": "blue", ":hover": {"background": "yellow"}}}
  ```
- **THEN** the framework SHALL generate pseudo-class attached without space:
  ```css
  .button[webcompy-cid-xxx] { color: blue; }
  .button[webcompy-cid-xxx]:hover { background: yellow; }
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
  @media (max-width: 768px) { 
    .button[webcompy-cid-xxx] { color: red; }
    .button[webcompy-cid-xxx]:hover { background: yellow; }
  }
  ```

### Requirement: Nested scoped style shall support all CSS at-rules and pseudo-selectors
The framework SHALL accept any string key in nested style dictionaries, allowing developers to use `@media`, `@supports`, `@container`, pseudo-classes (`:hover`, `:focus`, `:active`), and pseudo-elements (`::before`, `::after`). At-rules SHALL use wrapping syntax. Pseudo-selectors SHALL concatenate without space.

#### Scenario: Using @supports rule
- **WHEN** a developer defines:
  ```python
  {".card": {"padding": "20px", "@supports (display: grid)": {"display": "grid"}}}
  ```
- **THEN** the framework SHALL generate:
  ```css
  .card[webcompy-cid-xxx] { padding: 20px; }
  @supports (display: grid) { .card[webcompy-cid-xxx] { display: grid; } }
  ```

#### Scenario: Using pseudo-elements
- **WHEN** a developer defines:
  ```python
  {".tooltip": {"position": "relative", "::after": {"content": "attr(data-tip)"}}
  ```
- **THEN** the framework SHALL generate:
  ```css
  .tooltip[webcompy-cid-xxx] { position: relative; }
  .tooltip[webcompy-cid-xxx]::after { content: attr(data-tip); }
  ```

#### Scenario: Using combinator selectors in nested structure
- **WHEN** a developer defines:
  ```python
  {".menu": {"color": "black", "> li": {"color": "blue"}}}
  ```
- **THEN** the framework SHALL generate with space before combinator:
  ```css
  .menu[webcompy-cid-xxx] { color: black; }
  .menu[webcompy-cid-xxx] > li { color: blue; }
  ```
