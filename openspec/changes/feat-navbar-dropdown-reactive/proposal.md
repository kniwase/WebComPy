## Why

The docs_app navigation bar currently depends on Bootstrap 5 JavaScript (`bootstrap.bundle.min.js`) for dropdown toggle behavior. This creates an external dependency that conflicts with the goal of a Python-only frontend. Replacing the Bootstrap JS dropdown with a WebComPy reactive implementation demonstrates that WebComPy can handle interactive UI patterns natively, and lays groundwork for a future UI component library.

## What Changes

- Replace Bootstrap JS-dependent dropdown in `docs_app/components/navigation.py` with a pure WebComPy reactive implementation
- Use `Signal[bool]` for open/close state management
- Implement click-outside detection to close dropdowns
- Add proper ARIA attributes (`aria-expanded`, `aria-haspopup`, `aria-controls`) managed by reactive state
- Maintain existing visual structure while removing all Bootstrap class names (preparation for Tailwind migration)
- Remove `bootstrap.bundle.min.js` script from `docs_app/bootstrap.py`

## Capabilities

### New Capabilities
- `reactive-dropdown`: A self-contained dropdown component pattern using WebComPy's reactive system (`Signal`, `@click` handler, computed ARIA attributes) without external JavaScript dependencies.

### Modified Capabilities
- `components`: No requirement changes; the implementation pattern demonstrates how scoped styling and event handling can achieve Bootstrap-equivalent behavior.

## Impact

- `docs_app/components/navigation.py` — complete rewrite of dropdown logic
- `docs_app/bootstrap.py` — remove Bootstrap JS script
- `docs_app/layout.py` — no changes required
- No framework-level changes (this is a docs_app-only change)

## Known Issues Addressed

- No known issues directly addressed. This is a docs_app refactoring that reduces external dependencies.

## Non-goals

- Creating a reusable `webcompy.ui` dropdown component (that is a future change)
- Adding keyboard navigation support (Tab/Enter/Escape) — out of scope for this minimal replacement
- Changing the visual appearance beyond class name removal
- Adding animations or transitions
