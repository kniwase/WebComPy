## Why

The docs_app currently uses Bootstrap 5 CSS with custom `scoped_style` CSS-in-Python for styling. To modernize the documentation site's appearance, prepare for future UI component library development, and align with current frontend best practices, we want to migrate to Tailwind CSS. This enables rapid utility-first styling, built-in responsive design, and easy dark mode implementation. Additionally, we want to add a GitHub-like design with light/dark theme switching, and manage highlight.js themes locally for standalone/offline support.

## What Changes

- **Remove Bootstrap 5 CSS** from `docs_app/bootstrap.py`
- **Add Tailwind CSS CDN JS** (`static/tailwindcss.js`, downloaded from CDN for standalone mode)
- **Add highlight.js theme files** (`static/highlightjs/github-dark.min.css`, `static/highlightjs/github-dark-dimmed.min.css`)
- **Rewrite all docs_app component class names** from Bootstrap to Tailwind utility classes
  - `docs_app/components/navigation.py` — navbar with responsive mobile menu
  - `docs_app/components/demo_display.py` — card layout
  - `docs_app/pages/not_found.py` — 404 page
  - `docs_app/templates/home.py` — documentation sections and tables
- **Add light/dark theme toggle** to navbar
  - Use `Signal` for theme state
  - Use `app.set_html_attr("class", computed(...))` (requires `feat-html-attrs-control`)
  - Switch between `github-dark` and `github-light` (default) highlight.js themes
- **Preserve all `scoped_style` definitions** — Tailwind and scoped_style coexist
- **Maintain `standalone=True`** — all assets served locally

## Capabilities

### New Capabilities
- `tailwind-integration`: Using Tailwind CSS CDN with WebComPy applications, including local asset management for standalone mode.
- `theme-switching`: Runtime light/dark theme switching with reactive state management and CSS framework integration.

### Modified Capabilities
- `app-config`: `assets` field usage pattern (local CSS/JS files in `static/` directory).

## Impact

- `docs_app/bootstrap.py` — replace Bootstrap links/scripts with Tailwind CDN + local assets
- `docs_app/components/navigation.py` — Tailwind classes + theme toggle
- `docs_app/components/demo_display.py` — Tailwind card styling
- `docs_app/pages/not_found.py` — Tailwind styling
- `docs_app/templates/home.py` — Tailwind container/typography/table styling
- `static/` — new directory with `tailwindcss.js` and highlight.js themes
- No framework-level changes (relies on `feat-html-attrs-control`)

## Known Issues Addressed

- No known issues directly addressed. This is a docs_app design modernization.

## Non-goals

- Creating a reusable Tailwind integration plugin or component library
- Removing `scoped_style` usage (preserved as framework feature demonstration)
- Supporting system-level dark mode preference (manual toggle only)
- Custom Tailwind configuration beyond basic CDN usage
- Animations or page transitions
