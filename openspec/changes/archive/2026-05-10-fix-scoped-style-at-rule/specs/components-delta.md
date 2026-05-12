# Delta: Component System — Scoped CSS At-Rule Support

**Change**: `fix-scoped-style-at-rule`

**Type**: Bug fix — at-rule keys in `scoped_style` must not receive cid attribute scoping

---

## Modified Requirement

**Location**: `openspec/specs/components/spec.md`

**Current** (line 55-99):

The existing requirement "Scoped CSS shall support nested dictionary structures" covers nested at-rules but does not explicitly address **top-level** at-rule keys.

**Add the following scenario after line 99** (after "Scenario: Defining deeply nested structures"):

---

#### Scenario: Using at-rules as top-level keys in scoped style

- **WHEN** a developer defines an at-rule as a top-level key in `scoped_style`:

  ```python
  Component.scoped_style = {
      "@media (max-width: 768px)": {
          ".button": {"color": "red"}
      }
  }
  ```

- **THEN** the at-rule key itself SHALL NOT receive the `[webcompy-cid-{id}]` attribute
- **AND** selectors inside the at-rule block SHALL receive the `[webcompy-cid-{id}]` attribute
- **AND** the generated CSS SHALL be valid:

  ```css
  @media (max-width: 768px) { .button[webcompy-cid-xxx] { color: red; } }
  ```

- **AND** the at-rule syntax SHALL remain intact (no attribute selectors in `@media` declaration)

---

**Update the existing requirement text** (line 55) to clarify:

**Before:**

> ### Requirement: Scoped CSS shall support nested dictionary structures for media queries and pseudo-selectors

**After:**

> ### Requirement: Scoped CSS shall support nested dictionary structures for media queries, at-rules, and pseudo-selectors
> The framework SHALL allow developers to use CSS at-rules (`@media`, `@supports`, `@container`, etc.) as either top-level keys or nested keys in `scoped_style` dictionaries. At-rule keys themselves SHALL NOT receive the `[webcompy-cid-{id}]` attribute selector. Selectors inside at-rule blocks SHALL receive proper scoping.

---

## New Requirement

**Add after line 152** (after "Scenario: Using combinator selectors in nested structure"):

---

### Requirement: At-rule keys shall be detected by `@` prefix

The framework SHALL detect CSS at-rules by checking if the key starts with `@` (after stripping whitespace). This detection SHALL be used to skip cid attribute application to at-rule keys.

#### Scenario: At-rule detection with leading whitespace

- **WHEN** a developer uses leading whitespace in an at-rule key:

  ```python
  Component.scoped_style = {
      " @media (max-width: 768px)": {".button": {"color": "red"}}
  }
  ```

- **THEN** the framework SHALL classify the key as an at-rule (despite leading space)
- **AND** the at-rule SHALL NOT receive cid attribute scoping

#### Scenario: All standard CSS at-rules are supported

- **WHEN** a developer uses any standard CSS at-rule:

  ```python
  Component.scoped_style = {
      "@media (...)": {...},
      "@supports (...)": {...},
      "@container (...)": {...},
  }
  ```

- **THEN** all at-rules SHALL be detected by the `@` prefix
- **AND** none SHALL receive cid attribute scoping
- **AND** selectors inside all at-rule blocks SHALL receive proper scoping

---

## New Requirement: Nested at-rule support

### Requirement: Scoped CSS shall support nested at-rules

The framework SHALL support CSS at-rules nested inside other at-rules to arbitrary depth. Inner at-rules SHALL NOT receive cid attribute scoping. Their content SHALL be wrapped in `{ }` braces, and selectors at the deepest nesting level SHALL receive proper cid scoping.

#### Scenario: Nesting @supports inside @media

- **WHEN** a developer nests `@supports` inside `@media`:
  ```python
  Component.scoped_style = {
      "@media (max-width: 768px)": {
          "@supports (display: grid)": {".card": {"display": "grid"}}
      }
  }
  ```
- **THEN** the framework SHALL generate:
  ```css
  @media (max-width: 768px) { @supports (display: grid) { .card[webcompy-cid-xxx] { display: grid; } } }
  ```
- **AND** the inner at-rule SHALL NOT receive cid attribute scoping

#### Scenario: Triple-nested at-rules

- **WHEN** a developer nests at-rules three levels deep:
  ```python
  {"@media (...)": {"@supports (...)": {"@container (...)": {".card": {"display": "grid"}}}}}
  ```
- **THEN** the framework SHALL generate valid CSS with all three wrapping levels
- **AND** the innermost selector SHALL receive cid scoping

### Requirement: Scoped CSS shall support @keyframes

The framework SHALL support `@keyframes` at-rules used as top-level keys in `scoped_style`. `@keyframes` inner keys (`from`, `to`, `0%`, `100%`, etc.) SHALL NOT receive cid attribute scoping.

#### Scenario: Defining @keyframes as top-level key

- **WHEN** a developer defines `@keyframes` as a top-level key:
  ```python
  Component.scoped_style = {
      "@keyframes spin": {
          "0%": {"transform": "rotate(0deg)"},
          "100%": {"transform": "rotate(360deg)"},
      }
  }
  ```
- **THEN** the framework SHALL generate:
  ```css
  @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
  ```
- **AND** inner keys SHALL NOT receive cid attribute scoping

#### Scenario: @keyframes nested inside @media

- **WHEN** a developer nests `@keyframes` inside another at-rule:
  ```python
  {"@media (...)": {"@keyframes fade": {"from": {"opacity": "0"}, "to": {"opacity": "1"}}}}
  ```
- **THEN** the @keyframes inner keys SHALL NOT receive cid attribute scoping

### Requirement: Pseudo-class/element selectors inside at-rules shall be scoped

Pseudo-class (`:hover`, `:focus`) and pseudo-element (`::before`, `::after`) selectors used as direct children of at-rule blocks SHALL be scoped with `*[webcompy-cid-{cid}]` prefix to prevent leaking to elements outside the component.

#### Scenario: Pseudo-class as direct child of @media

- **WHEN** a developer uses `:hover` directly inside `@media`:
  ```python
  {"@media (max-width: 768px)": {":hover": {"background": "yellow"}}}
  ```
- **THEN** the framework SHALL generate:
  ```css
  @media (max-width: 768px) { *[webcompy-cid-xxx]:hover { background: yellow; } }
  ```

### Requirement: Combinator selectors inside at-rules shall be valid and scoped

Combinator selectors (`>`, `+`, `~`, descendant space) used as direct children of at-rule blocks SHALL be scoped without producing orphan attribute selectors.

#### Scenario: Combinator inside @media

- **WHEN** a developer uses `> li` directly inside `@media`:
  ```python
  {"@media (...)": {"> li": {"color": "blue"}}}
  ```
- **THEN** the generated CSS SHALL contain valid scoped selectors
- **AND** no orphan `[webcompy-cid-xxx]` attribute selectors SHALL appear before combinators

## Validation: Implementation Notes

- `_generate_css_recursive` receives an optional `cid` parameter to scope bare selectors inside top-level at-rule blocks.
- The getter handles at-rule wrapping (`{ }` braces) by iterating inner selectors separately.
- Non-at-rule paths do NOT pass `cid` to `_generate_css_recursive` to avoid orphan attribute selectors from combinator patterns.

**Unit Test examples are in `tests/test_scoped_style_generation.py`.**

---

## Related Changes

- `2026-05-09-feat-nested-scoped-style` — Introduced nested scoped style feature
- `2026-05-10-fix-scoped-style-css-output` — Fixed CSS output structure for nested at-rules
- This change — Fixes cid application to top-level at-rule keys
