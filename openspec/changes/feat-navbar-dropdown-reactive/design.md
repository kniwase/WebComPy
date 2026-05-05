## Context

The docs_app currently uses Bootstrap 5's navbar component with dropdown menus. The dropdown functionality depends on Bootstrap's JavaScript (`bootstrap.bundle.min.js`) which handles click events, toggle classes, and keyboard navigation. Since WebComPy is a Python frontend framework running in the browser via PyScript, relying on external JavaScript for basic UI interactions creates an unnecessary dependency and limits the framework's self-contained nature.

This change replaces the Bootstrap JS dropdown with a pure WebComPy implementation using the framework's built-in reactive system (`Signal`, `@click` handlers, `Computed`). This serves as a proof-of-concept that WebComPy can handle common UI patterns without external JS libraries.

## Goals / Non-Goals

**Goals:**
- Remove Bootstrap JS dependency from docs_app
- Implement dropdown open/close via WebComPy `Signal[bool]` state
- Maintain correct ARIA attributes for accessibility
- Support click-outside to close dropdown
- Preserve existing navbar structure and navigation behavior

**Non-Goals:**
- Creating a reusable `webcompy.ui` component (future work)
- Keyboard navigation (Tab/Enter/Escape) — minimal viable replacement
- Animations or transitions
- Changing visual design (only class name changes for Tailwind preparation)

## Decisions

### Decision: Use module-level Signal for dropdown state

Each dropdown will use a `Signal[bool]` for its open state. Multiple dropdowns will be supported via a dictionary keyed by index.

```python
open_states: dict[int, Signal[bool]] = {}
```

**Alternatives considered:**
- Single global Signal: doesn't support multiple dropdowns
- Component-local state via DI: overkill for this simple case
- Element-level state: no existing mechanism in WebComPy

### Decision: Click-outside detection via document click handler

Register a click handler on `browser.document` that closes all dropdowns when clicking outside any dropdown toggle or menu.

```python
@browser.document.addEventListener("click")
def close_dropdowns(event):
    if not is_click_inside_dropdown(event):
        for state in open_states.values():
            state.value = False
```

**Alternatives considered:**
- Click handler on each dropdown menu: doesn't catch clicks on sibling elements
- Overlay element behind dropdowns: adds unnecessary DOM elements

### Decision: Remove all Bootstrap classes, use semantic HTML + minimal styling

Since the next change will migrate to Tailwind CSS, remove Bootstrap-specific classes now and use semantic HTML structure. This avoids mixing Bootstrap and Tailwind classes.

## Risks / Trade-offs

- **[Risk]** Click-outside handler may interfere with other components using document click events → **Mitigation:** Use event.stopPropagation() appropriately; handler only sets Signal values
- **[Risk]** Removing Bootstrap classes before Tailwind migration leaves navbar unstyled temporarily → **Mitigation:** Add minimal inline styling or accept temporary visual regression between changes
- **[Risk]** No keyboard accessibility (Enter/Space to open, Escape to close, arrow navigation) → **Mitigation:** Document as known limitation; address in future UI library change

## Migration Plan

1. Implement reactive dropdown in `navigation.py`
2. Remove Bootstrap JS from `bootstrap.py`
3. Verify all dropdown menus open/close correctly
4. Verify navigation links still work

No breaking changes for users — this is an internal docs_app change only.

## Open Questions

None at this time.
