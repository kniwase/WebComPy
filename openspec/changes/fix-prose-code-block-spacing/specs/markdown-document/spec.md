# markdown-document delta: fix-prose-code-block-spacing

## MODIFIED Requirements

### Requirement: A prose typography preset stylesheet shall be provided opt-in

The framework SHALL ship a `prose.css` stylesheet under `webcompy/ui/_styles/`, registered in `_STYLES_FILES` so it is served at `/_webcompy-ui/prose.css` and copied during SSG like the other framework stylesheets. It SHALL NOT be imported by `index.css`. All rules SHALL be scoped under a `.prose` wrapper class and wrapped in `@layer prose`. Colors, spacing, and fonts SHALL reference the existing `tokens.css` CSS variables so the preset follows the active theme. The preset SHALL cover headings, paragraphs, lists, tables, blockquotes, horizontal rules, inline code, and code blocks. Code blocks SHALL receive symmetric vertical spacing (`margin: var(--space-4) 0`) from a `.prose pre` rule, and the code block stylesheet (`code-block.css`) SHALL be wrapped in `@layer components` so the layered preset rule takes precedence over the block's base `margin: 0`.

#### Scenario: Stylesheet served and copied

- **WHEN** the dev server or SSG output is inspected
- **THEN** `prose.css` is available at `/_webcompy-ui/prose.css` alongside the other framework stylesheets without being linked automatically

#### Scenario: Scoped and themed rules

- **WHEN** `prose.css` content is inspected
- **THEN** every rule selector is scoped under `.prose`, the rules live in `@layer prose`, and color/font values reference `tokens.css` variables rather than hard-coded values

#### Scenario: Code blocks have symmetric vertical spacing

- **WHEN** `prose.css` content is inspected
- **THEN** it contains a `.prose pre` rule setting `margin: var(--space-4) 0`

#### Scenario: Code block stylesheet participates in the layer system

- **WHEN** `code-block.css` content is inspected
- **THEN** its rules are wrapped in `@layer components`