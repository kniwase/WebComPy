# Design: feat-ui-disclosure-feedback-components

## Context

Second component family on the `ui-primitives` foundation. Collapse and the Accordion built from it consume the `transition` capability for animated expand/collapse; Tabs switches instantly while keeping panels mounted (see D2), and the remaining components (Alert, Progress, Badge, Skeleton, Card) are static or near-static and need only the foundation contracts. No Teleport dependency — all components render in place.

Grounded facts (verified in codebase):

- docs_app already has an ad-hoc `DocsCard` (`docs_app/components/ui.py:19-38`, scoped styles at `:120`) to promote; its scoped-style pattern shows the token-consuming style shape the themed layer standardizes.
- Function-style components with `TypedDict` props and reactive prop values are the established pattern, and every component is a named custom element (`@define_component(custom_element_name=...)`; single-word names cannot be derived because custom-element tags must contain a hyphen). The Transition element (preceding change) accepts a child generator, which Collapse uses for animated expand/collapse.
- `primitives.css` (introduced by the foundation change and extended by the overlay change) is the delivery point for themed rules inside `@layer components`.

## Goals / Non-Goals

**Goals:**

- Seven headless/themed pairs (Tabs, Collapse/Accordion, Alert, Progress, Badge, Skeleton, Card) with correct ARIA contracts and keyboard behavior.
- Transition integration for collapse/expand animation (Collapse, and the Accordion composed from it). Tabs switches instantly with state-preserving hidden panels (D2).
- Consistent `data-state` vocabularies and class pass-through per the foundation contract.

**Non-Goals:**

- Vertical tabs, nested accordions beyond one level, alert queues, advanced skeleton variants, content lazy-loading, and Tabs panel-switch animation (see proposal Non-goals).

## Decisions

### D1: Tabs — automatic activation, wrapping arrow keys

Keyboard model follows the WAI-ARIA APG tab pattern with automatic activation: Left/Right arrows move focus and activate the adjacent tab (wrapping), Home/End jump to first/last. Rationale for automatic over manual activation: WebComPy panels are local DOM with no fetch-on-activate cost, which is precisely the case the APG recommends automatic activation for. Each tab carries `role="tab"`, `aria-selected`, `aria-controls`; panels carry `role="tabpanel"` and are hidden when inactive.

### D2: Tabs render all panels, hide inactive ones

All panels render and stay mounted; inactive panels are hidden with the boolean `hidden` attribute, preserving internal state (form inputs, scroll position, component lifecycle) across switches. Switching is instant. Rationale:

- Instant activation with state preservation is the primary value of a local tab widget; it is exactly what the WAI-ARIA APG pattern and downstream kits optimize for.
- Panel switching animates through element *replacement*, which is outside the Transition capability's contract: the transition spec patches same-tag children in place without running a class sequence, so a Transition-driven swap cannot be guaranteed to animate (two framework `div` panels are always same-tag; user content of equal type likewise patches). Rather than keep spec wording the framework cannot deliver, Tabs carries no switch animation in v1.

Alternative (active-only mounting, the Radix model) rejected: it loses panel-internal state and buys no animation for the same reason. Applications that want a visual flourish can bind CSS animations to the panels' `data-state` changes themselves; this is documented as a non-goal.

### D3: Collapse animation via Transition with a CSS height technique

Expand/collapse animates through the Transition protocol on the content wrapper. CSS cannot transition `height: auto`, so the themed default uses the grid-template-rows technique (`grid-template-rows: 0fr → 1fr` on the content element, its direct children clamped with `overflow: hidden; min-height: 0`), which animates to natural content height without measurement. The headless layer only drives classes/`data-state`; the technique lives in themed CSS and is documented so headless users can substitute their own. Alternative (JS measurement of scrollHeight) rejected: it requires frame-synced style writes and resize handling, contradicting the CSS-only stance.

Transition integration constraints (verified against the transition spec after the rebase onto the baseline that includes it):

- The Transition child SHALL be a single element owning exactly one real DOM node; the animated node is a plain `div` wrapper rendered inside the component (not a component element, whose custom-element wrapper computes to `display: contents` and triggers the display warning).
- The transitioned wrapper's `class` attribute SHALL be a static string, never a signal-bound attribute, because a signal-driven class rewrite clobbers the `-enter-*`/`-leave-*` classes mid-sequence (documented limitation of the transition spec).
- `enter-from`/`leave-to` rules SHALL be declared after the steady rule so they win at equal specificity within `@layer components`.
- Duration resolves from the computed `transition` on the `-enter-active`/`-leave-active` classes (same pattern as the modal/drawer rules in the primitives stylesheet).
- Content unmount on close means the content element only exposes `data-state="open"` while mounted (including its leave sequence).

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

The docs_app replacement wraps the themed Card in a `div.ui-card` rather than passing `class_name` through. Scoped-style selectors are qualified with the owning component's id attribute, which lands on the Card element itself, not on the headless root div the class reaches inside the composed child; passing `class_name` would therefore leave the docs page's own `.ui-card` rule unable to match. The wrapper div carries the scoping attribute and the margin, so the layout rule continues to apply.

### D9: data-state vocabularies

- Tabs: `data-state="active" | "inactive"` on both tab and panel elements; inactive panels stay mounted and hidden.
- Collapse/Accordion triggers: `data-state="open" | "closed"`; Collapse content carries `data-state="open"` while mounted (including its leave sequence).
- Progress: `data-state="determinate" | "indeterminate"`.
- Alert/Badge/Skeleton/Card: no interaction state (static vocabularies only, e.g. variant attributes).

### D10: State control model — uncontrolled by default, controllable by prop

Collapse (and, for dismissal, Alert) resolve their state the way the overlay components resolve `open`: when the state prop is omitted the component owns internal `use_state` and toggles itself (this is what makes "trigger activates while closed → becomes open" work standalone); when the prop is a `SignalBase` instance the component writes through the signal and still invokes the optional callback; when the prop is a plain value the component never mutates it and delegates every change to the callback so the parent drives state. This mirrors the `isinstance(open_raw, SignalBase)` pattern established in the headless Dropdown/Modal.

### D11: Item content passed via items props, not named slots

Tabs and Accordion take a `tabs`/`items` list of dicts (`key`, `label`, `content: Callable[[], Element]`). The framework must know the key/label set to render the tablist (or the item triggers), so the keys necessarily live in a prop; letting the same prop carry the content generator keeps keys, labels, and panels in a single source of truth and matches the `Transition(name, generator)` idiom. Named slots cannot express a dynamic item count without string-concatenated slot names (`panel-<key>`), a known mismatch footgun. The overlay decision to supply Dropdown menu items via slots stays untouched: there the item set is opaque user markup the framework does not enumerate.

### D12: Hydration-stable DOM ids via a shared private helper

Tabs and Collapse derive `aria-controls`/`aria-labelledby` ids from the instance's hydration-stable `transfer_id`, the mechanism the overlay components use. The implementation extracts the existing private `overlay_dom_id(kind, context)` into a neutral private helper `component_dom_id` in `webcompy/ui/headless/_dom_id.py`, and `_overlay_utils.overlay_dom_id` becomes a thin delegation so overlay output ids are unchanged. Disclosure components consume the shared helper rather than duplicating it.

## Risks / Trade-offs

- **All-panels-rendered** (D2): every panel's content is created and mounted up front, so large panel sets pay full render cost immediately and content generators must not assume they run lazily on activation. Accepted for state preservation and the reliable instant switching it enables.
- **Grid-rows technique support**: requires modern browsers (grid-template-rows animation). Acceptable for the PyScript-era baseline; fallback is instant show/hide (transition simply does not animate where unsupported — the duration resolution handles this with immediate finalization).
- **Automatic activation** (D1): keyboard users traversing tabs switch panels at each step; with local panels this is the intended UX.
- **Accordion nesting**: one level supported; deeper nesting is untested and documented as unsupported.
