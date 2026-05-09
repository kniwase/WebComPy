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

## Validation

**Unit Test** (add to `tests/test_scoped_style_generation.py`):

```python
def test_top_level_media_at_rule():
    gen = ComponentGenerator("TestComponent", lambda ctx: None)
    gen.scoped_style = {
        "@media (max-width: 768px)": {
            ".btn": {"color": "red"}
        }
    }
    css = gen.scoped_style
    assert "@media (max-width: 768px) {" in css
    assert "@media[webcompy-cid-" not in css  # At-rule itself not scoped
    assert ".btn[webcompy-cid-" in css  # Selector inside is scoped
    assert "{ color: red; }" in css
```

**E2E Test** (add to `tests/e2e/test_scoped_style.py`):

```python
def test_scoped_style_top_level_media_query(page_on):
    page = page_on("/scoped-style")
    style_content = page.locator("style").first.evaluate("el => el.textContent")
    
    # Verify at-rule syntax is valid (no cid in @media declaration)
    assert "@media (max-width:" in style_content or "@media(max-width:" in style_content.replace(" ", "")
    assert "@media[webcompy-cid-" not in style_content  # Invalid syntax
    
    # Verify selectors inside are scoped
    assert "webcompy-cid-" in style_content
```

---

## Related Changes

- `2026-05-09-feat-nested-scoped-style` — Introduced nested scoped style feature
- `2026-05-10-fix-scoped-style-css-output` — Fixed CSS output structure for nested at-rules
- This change — Fixes cid application to top-level at-rule keys
