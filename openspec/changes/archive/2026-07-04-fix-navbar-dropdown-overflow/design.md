## Context

The docs_app navbar uses `position: absolute` with `left: 0` for dropdown menus. All navigation items are inside `.navbar-right`, which is pushed to the right side of the page via `margin-left: auto`. When a rightmost item (e.g., "Demos") opens its dropdown, `left: 0` positions the dropdown's left edge at the parent's left edge — but since the parent is near the right viewport boundary, the dropdown extends beyond the screen.

No viewport overflow protection exists in the navbar CSS because the issue was only surfaced as nav items were added to the right side.

## Goals / Non-Goals

**Goals:**
- Prevent navbar dropdowns from overflowing the right viewport edge on desktop (>768px viewport)
- Keep the fix minimal — one CSS property change
- Maintain readability: all dropdown content must be fully visible

**Non-Goals:**
- Changing the navbar layout structure (no DOM reordering, no new wrappers)
- Mobile menu behavior (separate CSS via `@media (max-width: 768px)` uses `position: static` — unaffected)
- JavaScript-based positioning or dynamic flip detection
- Framework-wide dropdown component (this is docs_app-specific)
- Spec changes to existing framework specs (no requirement-level behavior changes)

## Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Positioning strategy | `right: 0` instead of `left: 0` | All dropdown parents are in `.navbar-right` (right side of layout). Right-aligning the dropdown to the parent keeps it within the viewport. |
| Alternatives considered | `left: 50%; transform: translateX(-50%)` | Centering could still overflow on small desktop screens. Also changes visual alignment from current expectations. |
| Alternatives considered | JS-based flip detection | Overkill for a one-line CSS fix. No dynamic content widths justify it. |
| Approach scope | CSS-only, single property | Matches the principle of minimal intervention. The existing `position: relative` on parent, `z-index`, and other properties work correctly. |

## Risks / Trade-offs

- **[Visual change]** Dropdowns shift from left-aligned to right-aligned under their parent toggle. For "Demos" (rightmost item), this is invisible improvement. For potential left-side items (currently none with children), the dropdown would extend leftward — this is a standard pattern in nav frameworks (Bootstrap, etc.) and acceptable.
- **[Mobile unaffected]** Verified: `.navbar-dropdown` becomes `position: static` at ≤768px, so this change has zero effect on mobile layout.
