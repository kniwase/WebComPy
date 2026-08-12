# Transition

## Purpose

WebComPy provides a `Transition` element for CSS-class-driven enter/leave animations of a single conditional child. When a child appears or disappears due to a client-side state change, the framework owns class timing and delayed DOM removal following Vue 3's `<Transition>` class protocol, while users supply plain CSS. Duration resolution, node accounting, sequential replacement, SSR/hydration steady state, and reduced-motion support are specified so that animation never corrupts DOM structure or violates framework invariants.

## Requirements

### Requirement: Transition shall drive a Vue-compatible enter class sequence for appearing children

`Transition({"name": "<prefix>"}, child_generator)` SHALL be a public element exported from `webcompy.elements`, wrapping a generator that returns at most one child element or `None`. When a child appears due to a client-side state change, the framework SHALL mount the child's node, apply the class `{name}-enter-from`, and on the next animation frame replace it with `{name}-enter-active` and `{name}-enter-to`. When the enter duration elapses (end event or timeout, per the duration resolution requirement), the framework SHALL remove all three classes, leaving the node in its steady state. The class names SHALL follow Vue 3's `<Transition>` naming exactly.

#### Scenario: Enter sequence class order

- **WHEN** a Signal toggles from false to true and the Transition's generator yields a child element with `name` set to `fade`
- **THEN** the mounted node SHALL first carry the class `fade-enter-from`
- **AND** on the next animation frame SHALL carry `fade-enter-active` and `fade-enter-to` instead
- **AND** after the enter duration elapses SHALL carry none of the three classes

### Requirement: Transition shall intercept removal and drive a leave class sequence before deleting the node

When the generator stops yielding a child (returns `None`) while a child node exists, the framework SHALL NOT remove the node immediately. It SHALL apply `{name}-leave-from`, on the next animation frame replace it with `{name}-leave-active` and `{name}-leave-to`, keep the node mounted until the leave duration elapses (end event or timeout), and only then remove the node through the standard removal path (including callback-consumer destruction).

#### Scenario: Leave sequence delays removal

- **WHEN** a Signal toggles from true to false while the Transition's child is mounted, with `name` set to `fade`
- **THEN** the node SHALL remain in the document with class `fade-leave-from`, then `fade-leave-active` and `fade-leave-to` on the next animation frame
- **AND** the node SHALL be removed from the document only after the leave duration elapses

#### Scenario: Removing the Transition itself while a child is present

- **WHEN** the Transition element is removed from the tree (e.g. its own condition becomes false) while a child node is mounted
- **THEN** the child node SHALL be removed and its callback consumers destroyed without waiting for a leave sequence, and no orphaned node SHALL remain

### Requirement: Transition durations shall resolve from prop, computed styles, or immediate removal, always backed by a timeout

The enter/leave duration SHALL resolve in this order: (1) an explicit `duration` prop in milliseconds when provided; (2) otherwise, the longest duration parsed from the node's computed transition/animation styles in the browser; (3) otherwise, zero — the node finalizes immediately and a warning SHALL be logged. Regardless of the source, a timeout SHALL finalize each sequence even if `transitionend`/`animationend` events never arrive; end events arriving before the timeout SHALL finalize early. End-event listeners SHALL be removed upon finalization.

#### Scenario: Explicit duration prop wins

- **WHEN** `Transition({"name": "fade", "duration": 100}, generator)` runs a leave sequence
- **THEN** the node SHALL be removed approximately 100 milliseconds after the leave classes are applied, regardless of computed styles

#### Scenario: No applicable CSS removes immediately with a warning

- **WHEN** no `duration` prop is given and the node's computed styles define no transition or animation
- **THEN** the framework SHALL log a warning and finalize the sequence immediately

#### Scenario: Timeout finalizes when end events never fire

- **WHEN** a leave sequence runs with a resolved positive duration but no `transitionend`/`animationend` event is delivered
- **THEN** the timeout SHALL remove the node when the duration elapses

### Requirement: Transition shall keep node accounting consistent during sequences

While an enter or leave sequence runs, the Transition SHALL report its occupied node count as if the child were present, so sibling node indices remain valid. When a leave sequence completes and the node is removed, the Transition SHALL report zero occupied nodes and the parent SHALL re-index its children exactly once. During sequences no duplicate or missing sibling positions SHALL occur.

#### Scenario: Siblings stay stable during a leave

- **WHEN** an element tree contains a text node, a Transition with a leaving child, and another text node in sequence
- **THEN** the trailing text node SHALL keep its position while the leave runs
- **AND** after the leave completes, the parent SHALL re-index once and the trailing text node SHALL occupy the position immediately after the Transition's (now empty) slot

### Requirement: Child replacement shall be sequential, and interruption shall clean up

When the generator's result changes from one element to a different element, the old child SHALL complete or be terminated through its leave handling before the new child's enter sequence starts; the two children SHALL NOT occupy the tree simultaneously. When a new child appears while a leave sequence is in progress, the leaving node SHALL be finalized immediately (classes removed, node removed) before the enter sequence starts. When the generator re-yields an element with the same tag as the leaving child while a leave sequence is in progress, the leave SHALL NOT be interrupted: the leaving node SHALL remain mounted until the leave duration elapses, and the re-yielded element SHALL then mount and run its enter sequence.

#### Scenario: Replacement leaves then enters

- **WHEN** the generator yields element A and later yields element B without an intervening `None`
- **THEN** element A's leave sequence SHALL run to completion (or interruption per this requirement) before element B's enter sequence starts
- **AND** at no point SHALL both A's and B's nodes occupy the Transition's slot simultaneously

#### Scenario: Same-tag update during leave does not interrupt

- **GIVEN** a Transition whose generator yields a `div` element when either of two signals is true, and the child is leaving because both became false
- **WHEN** the second signal becomes true again while the leave sequence is in progress
- **THEN** the leaving node SHALL remain mounted until the leave duration elapses
- **AND** after the leave completes, the element SHALL mount again and run its enter sequence

### Requirement: Transition shall render the steady state on initial render without an enter sequence

During server-side rendering, static generation, hydration adoption, and the first browser render of the app, a Transition's current child (if any) SHALL be rendered without any transition classes, and no enter sequence SHALL run. Enter sequences SHALL run only for children created by client-side state changes after the initial render.

#### Scenario: SSR output has no transition classes

- **WHEN** a page containing a Transition with a present child is server-rendered
- **THEN** the SSR HTML SHALL contain the child markup without any `{name}-enter-*` or `{name}-leave-*` classes

#### Scenario: Hydrated content does not animate

- **WHEN** the application hydrates with a Transition whose child is already present
- **THEN** the child SHALL appear without an enter sequence

#### Scenario: First browser render does not animate

- **WHEN** a Transition with a present child is part of the initial client-side render of the app (no SSR)
- **THEN** the child SHALL appear without an enter sequence

### Requirement: Transition shall validate the child shape and props

The generator SHALL return either `None` or a single element that owns exactly one real DOM node (`ElementBase`, including `Component` roots). Multi-node shapes (`DynamicElement` subclasses such as `Fragment`, `Teleport`, `switch`, `repeat`, `Suspense`) and non-element shapes (text nodes, signals, raw strings) SHALL raise a framework validation error (`WebComPyException`) when encountered. The `name` prop SHALL be a required non-empty string; the `duration` prop, when provided, SHALL be a non-negative number of milliseconds. Invalid props SHALL raise a framework validation error.

#### Scenario: Invalid child shape is rejected

- **WHEN** a Transition's generator returns a `Fragment` (or another multi-node dynamic element)
- **THEN** rendering or refreshing the Transition SHALL raise `WebComPyException`
- **AND** no partial DOM insertion SHALL occur

#### Scenario: Missing name is rejected

- **WHEN** `Transition({}, generator)` is constructed
- **THEN** construction SHALL raise `WebComPyException`

### Requirement: Transition shall honor prefers-reduced-motion

The framework SHALL provide a media-query capability to detect `prefers-reduced-motion: reduce` (browser: the corresponding media query; server: false). When reduced motion is preferred, `Transition` SHALL skip class sequences entirely: appearing children SHALL mount immediately without enter classes, and disappearing children SHALL be removed immediately without leave classes.

#### Scenario: Reduced motion skips sequences

- **WHEN** the user's media preference is `prefers-reduced-motion: reduce` and a Transition's child appears and later disappears
- **THEN** the child node SHALL be mounted and removed immediately without any transition classes being applied
