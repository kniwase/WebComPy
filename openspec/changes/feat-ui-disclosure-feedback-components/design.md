# Design: feat-ui-disclosure-feedback-components

## Context

Second component family on the `ui-primitives` foundation. Tabs and Collapse consume the `transition` capability for animated state changes; the remaining components (Alert, Progress, Badge, Skeleton, Card) are static or near-static and need only the foundation contracts. No Teleport dependency — all components render in place.

Grounded facts (verified in codebase):

- docs_app already has an ad-hoc `Card` (`docs_app/components/ui.py:19-37`) to promote; its scoped-style pattern shows the token-consuming style shape the themed layer standardizes.
- Function-style components with `TypedDict` props and reactive prop values are the established pattern; the Transition element (preceding change) accepts a child generator, which Collapse/Tabs use for animated content switching.
- `primitives.css` (introduced by the foundation change) is the delivery point for themed rules inside `@layer components`.

## Goals / Non-Goals

**Goals:**

- Seven headless/themed pairs (Tabs, Collapse/Accordion, Alert, Progress, Badge, Skeleton, Card) with correct ARIA contracts and keyboard behavior.
- Transition integration for tab panel switching and collapse expand/collapse.
- Consistent `data-state` vocabularies and class pass-through per the foundation contract.

**Non-Goals:**

- Vertical tabs, nested accordions beyond one level, alert queues, advanced skeleton variants, content lazy-loading (see proposal Non-goals).

## Decisions

### D1: Tabs — automatic activation, wrapping arrow keys

Keyboard model follows the WAI-ARIA APG tab pattern with automatic activation: Left/Right arrows move focus and activate the adjacent tab (wrapping), Home/End jump to first/last. Rationale for automatic over manual activation: WebComPy panels are local DOM with no fetch-on-activate cost, which is precisely the case the APG recommends automatic activation for. Each tab carries `role="tab"`, `aria-selected`, `aria-controls`; panels carry `role="tabpanel"` and are hidden when inactive.

### D2: Tabs render all panels, hide inactive ones

All panels render; inactive panels are hidden (not removed), preserving internal state (form inputs, scroll) across switches and keeping the DOM stable. Panel switching animates via an optional Transition wrapper around the active panel content (themed default; disable-able). Alternative (lazy mount active panel only) rejected for v1: it destroys panel state on switch and complicates focus management; applications needing lazy content can compose it themselves since tab state is exposed.

### D3: Collapse animation via Transition with a CSS height technique

Expand/collapse animates through the Transition protocol on the content wrapper. CSS cannot transition `height: auto`, so the themed default uses the grid-template-rows technique (`grid-template-rows: 0fr → 1fr` with an inner overflow-hidden wrapper), which animates to natural content height without measurement. The headless layer only drives classes/`data-state`; the technique lives in themed CSS and is documented so headless users can substitute their own. Alternative (JS measurement of scrollHeight) rejected: it requires frame-synced style writes and resize handling, contradicting the CSS-only stance.

### D4: Accordion as Collapse composition with an open-policy signal

Accordion composes multiple Collapse items and owns a shared open-state (set of open item keys, or a single key when the single-open policy prop is set). Item triggers toggle through this shared state. Rationale: composition keeps Collapse independently useful and the policy logic trivial; single-open is the common request, multi-open the default.

### D5: Alert role mapping by variant

Error and warning variants render `role="alert"` (assertive announcement); info and success render `role="status"` (polite). Dismissable alerts include an accessible dismiss button. Rationale: matches the urgency semantics users expect and keeps announcement behavior correct without configuration.

### D6: Progress determinate/indeterminate ARIA

Determinate progress renders `role="progressbar"` with `aria-valuenow`/`aria-valuemin`/`aria-valuemax` from value props. Indeterminate mode omits `aria-valuenow` (per ARIA, a progressbar without valuenow is indeterminate) and exposes `data-state="indeterminate"`. An accessible label prop is required (aria-label/labelled-by).

### D7: Skeleton is decorative

Skeleton placeholders render `aria-hidden="true"` (they are visual loading decoration); the surrounding container carries the accessible loading indication (e.g. a Spinner with `role="status"` or text). Documented guidance pairs Skeleton with the Spinner component for correct announcements.

### D8: Card promoted from docs_app

Card becomes a structural headless component (header/body/footer regions via children props) with themed token styling; docs_app's ad-hoc Card is replaced. No behavior beyond structure — Card exists so layout containers share tokens and class hooks instead of each app re-deriving them.

### D9: data-state vocabularies

- Tabs: `data-state="active" | "inactive"` on tabs; panels hidden when inactive.
- Collapse/Accordion triggers and content: `data-state="open" | "closed"`.
- Progress: `data-state="determinate" | "indeterminate"`.
- Alert/Badge/Skeleton/Card: no interaction state (static vocabularies only, e.g. variant attributes).

## Risks / Trade-offs

- **All-panels-rendered** (D2): large panel sets pay full render cost upfront. Accepted for state preservation; documented, with composition guidance for lazy needs.
- **Grid-rows technique support**: requires modern browsers (grid-template-rows animation). Acceptable for the PyScript-era baseline; fallback is instant show/hide (transition simply does not animate where unsupported — the duration resolution handles this with immediate finalization).
- **Automatic activation** (D1): keyboard users traversing tabs switch panels at each step; with local panels this is the intended UX.
- **Accordion nesting**: one level supported; deeper nesting is untested and documented as unsupported.
