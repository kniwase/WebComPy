# Spec Delta

## MODIFIED Requirements

### Requirement: The docs section shall be responsive

On wide viewports the layout SHALL show sidebar, content, and TOC. Below the wide breakpoint the TOC aside SHALL be hidden. Below the mobile breakpoint the sidebar SHALL collapse behind a toggle (following the Navbar mobile precedent), and content SHALL remain fully readable without either aside. Grid track definitions (`minmax(0, 1fr)`) and flex/grid container constraints (`min-width: 0`) SHALL prevent wide content (including tables and long inline code) from expanding the center column, colliding with the sticky TOC aside at desktop/tablet widths (`1100px`–`1440px`), or causing document-level horizontal overflow (`scrollWidth > clientWidth`) on mobile (`390px`), tablet (`1024px`), or desktop viewports.

#### Scenario: Mobile layout

- **WHEN** a docs page is viewed on a narrow viewport (such as `390px`)
- **THEN** the sidebar is hidden until toggled and the TOC is not rendered visibly
- **AND** wide tables scroll inside their wrapper and `document.documentElement.scrollWidth <= document.documentElement.clientWidth`

#### Scenario: Desktop and tablet layout without TOC overlap

- **WHEN** a docs page containing wide tables or code spans is viewed at `1100px`, `1280px`, or `1440px`
- **THEN** the `.docs-content` column SHALL NOT overflow into `.docs-toc`
- **AND** `document.documentElement.scrollWidth <= document.documentElement.clientWidth`

## ADDED Requirements

### Requirement: Statically generated docs theme toggle and 404 fallback SHALL hydrate without mismatches

Reloading a statically generated docs page with a `webcompy-theme` cookie or visiting an unmatched path served via `404.html` SHALL synchronize client state cleanly so `RenderContext.hydration_report` remains empty and no hydration warning or `.py-error` banner appears.

#### Scenario: Visiting an unmatched path via static 404.html

- **WHEN** a browser loads `/this-page-does-not-exist-404` on the statically generated docs site
- **THEN** the `NotFound` page SHALL render without hydration mismatch warnings or DOM `.py-error` elements

#### Scenario: Reloading a docs page with a persisted theme cookie

- **WHEN** a user toggles the docs theme control to `dark` or `light` and reloads any docs route
- **THEN** the persisted theme and `ThemeToggle` label/state SHALL synchronize cleanly with zero hydration mismatches
